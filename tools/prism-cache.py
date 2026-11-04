#!/usr/bin/env python3
"""Fetch and verify Prism metadata JSON only; never fetch game/runtime payloads."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.request import urlopen

BASE_URL = "https://meta.prismlauncher.org/v1"
MAX_BYTES = 4 * 1024 * 1024
UID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def safe_token(value, pattern, label):
    if not isinstance(value, str) or not pattern.fullmatch(value) or value in (".", ".."):
        raise ValueError(f"unsafe {label}: {value!r}")
    return value


def fetch_json(url):
    with urlopen(url, timeout=30) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError(f"metadata exceeds {MAX_BYTES} byte limit: {url}")
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid metadata JSON: {url}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"metadata must be a JSON object: {url}")
    return data, value


def ensure_cache_root(root):
    root = Path(root).expanduser().absolute()
    dist = (Path(__file__).resolve().parents[1] / "dist").resolve()
    resolved = root.resolve()
    if resolved == dist or dist in resolved.parents:
        raise ValueError("cache root must be outside the repository dist directory")
    # Reject symlinks in the cache path so publication cannot escape the chosen root.
    current = Path(root.anchor)
    for part in root.parts[1:]:
        current = current / part
        if current.exists() and current.is_symlink():
            raise ValueError(f"cache path contains symlink: {current}")
    root.mkdir(parents=True, exist_ok=True)
    return root


def publish(root, uid, filename, data, expected_sha256=None):
    safe_token(uid, UID_RE, "component UID")
    safe_token(filename, ID_RE, "metadata filename")
    target_dir = root
    for part in ("meta", uid):
        target_dir = target_dir / part
        try:
            target_dir.mkdir()
        except FileExistsError:
            pass
        if target_dir.is_symlink() or not target_dir.is_dir():
            raise ValueError(f"cache path is not a real directory: {target_dir}")
    target = target_dir / filename
    digest = hashlib.sha256(data).hexdigest()
    if expected_sha256 is not None and digest.lower() != expected_sha256.lower():
        raise ValueError(f"SHA-256 mismatch for {uid}/{filename}: expected {expected_sha256}, got {digest}")
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_file():
            raise ValueError(f"refusing to replace non-regular cache file: {target}")
        old = hashlib.sha256(target.read_bytes()).hexdigest()
        if old != digest:
            raise FileExistsError(f"refusing to replace existing metadata with different content: {target}")
        return target
    fd, temp_name = tempfile.mkstemp(prefix=".prism-meta-", dir=target_dir)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # link() is exclusive: a racing writer cannot have its file overwritten.
        os.link(temp_name, target)
    except FileExistsError:
        if target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise FileExistsError(f"refusing to replace existing metadata: {target}")
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
    return target


def get_index(root, uid, indexes):
    safe_token(uid, UID_RE, "component UID")
    if uid not in indexes:
        data, index = fetch_json(f"{BASE_URL}/{uid}/index.json")
        if index.get("formatVersion") != 1 or not isinstance(index.get("versions"), list):
            raise ValueError(f"unsupported Prism index schema for {uid}")
        publish(root, uid, "index.json", data)
        indexes[uid] = index
    return indexes[uid]


def choose_version(root, uid, constraint, indexes):
    index = get_index(root, uid, indexes)
    entries = index["versions"]
    if constraint:
        exact = [e for e in entries if e.get("version") == constraint]
        if not exact:
            raise ValueError(f"required Prism version not found: {uid}={constraint}")
        return exact[0]
    # `suggests` is advisory: use it when listed, otherwise the recommended
    # version. Prism's order is newest first, so keep its first recommended.
    recommended = [e for e in entries if e.get("recommended") is True]
    if not recommended:
        raise ValueError(f"no recommended Prism version for dependency {uid}")
    return recommended[0]


def fetch_component(root, uid, version, indexes, done, active):
    safe_token(uid, UID_RE, "component UID")
    safe_token(version, ID_RE, "version ID")
    key = (uid, version)
    if key in done:
        return
    if key in active:
        raise ValueError(f"Prism metadata dependency cycle: {uid}={version}")
    active.add(key)
    index = get_index(root, uid, indexes)
    entry = next((e for e in index["versions"] if e.get("version") == version), None)
    if entry is None:
        raise ValueError(f"version missing from Prism index: {uid}={version}")
    digest = entry.get("sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
        raise ValueError(f"Prism index lacks a valid SHA-256 for {uid}={version}")
    data, metadata = fetch_json(f"{BASE_URL}/{uid}/{version}.json")
    if metadata.get("uid", uid) != uid or metadata.get("version", version) != version:
        raise ValueError(f"Prism metadata identity mismatch: {uid}={version}")
    publish(root, uid, f"{version}.json", data, digest)
    requires = metadata.get("requires", [])
    if not isinstance(requires, list):
        raise ValueError(f"invalid Prism requires list: {uid}={version}")
    for requirement in requires:
        if not isinstance(requirement, dict) or not isinstance(requirement.get("uid"), str):
            raise ValueError(f"invalid Prism requirement in {uid}={version}")
        dep_uid = safe_token(requirement["uid"], UID_RE, "required UID")
        exact = requirement.get("equals")
        suggestion = requirement.get("suggests")
        if exact is not None and not isinstance(exact, str):
            raise ValueError(f"invalid exact Prism requirement for {dep_uid}")
        if suggestion is not None and not isinstance(suggestion, str):
            raise ValueError(f"invalid suggested Prism requirement for {dep_uid}")
        selected = choose_version(root, dep_uid, exact or suggestion, indexes)
        fetch_component(root, dep_uid, selected.get("version"), indexes, done, active)
    active.remove(key)
    done.add(key)


def cache(root, version):
    safe_token(version, ID_RE, "version ID")
    root = ensure_cache_root(root)
    indexes, done, active = {}, set(), set()
    fetch_component(root, "net.minecraft", version, indexes, done, active)
    return root


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="metadata cache root (outside dist)")
    parser.add_argument("--version", default="26.4-snapshot-6", help="Minecraft Prism version ID")
    args = parser.parse_args(argv)
    root = cache(args.root, args.version)
    print(f"Verified Prism metadata cached under {root}/meta.")
    print("Metadata only: installation is incomplete until legitimate game files are imported.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
