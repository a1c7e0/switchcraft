#!/usr/bin/env python3
"""Combine immutable tested artifacts into one SD-root ZIP without rebuilding VMs."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
APPS = (
    "switch-diagnostics", "java-test", "ffi-test", "zero-services-test",
    "vulkan-test", "vulkan-present", "java25-test", "switchcraft-java25",
    "minecraft-launcher",
)
TEST_JARS = (
    "diagnostic-tests.jar", "dependency.jar", "java25-hello.jar", "java25-tests.jar",
    "java25-agent-smoke-agent.jar", "java25-agent-smoke-app.jar", "switchcraft-native-smoke.jar",
)
DOCS = (
    "DEVICE_TEST_QUICKSTART.md", "TEST_PLAN.md", "LAUNCHER_TESTS.md", "PRISM_PORT.md",
    "HOST_REFERENCE.md", "KNOWN_ISSUES.md", "SD_TEST_PACKAGE.md",
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_input(directory, filename, pin, runtime):
    archive, manifest = directory / filename, directory / "manifest.json"
    if file_sha(archive) != pin["zip_sha256"] or file_sha(manifest) != pin["manifest_sha256"]:
        raise RuntimeError("Input archive or manifest differs from the immutable pin: " + str(directory))
    record = json.loads(manifest.read_text())
    if record["source_revision"] != pin["source_revision"] or record["java_switch_revision"] != runtime:
        raise RuntimeError("Input source/runtime revision mismatch")
    return archive, record


def read_archive(path):
    result = {}
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            name = member.filename
            parts = PurePosixPath(name)
            if (parts.is_absolute() or ".." in parts.parts or "\\" in name
                    or str(parts) != name.rstrip("/") or name in result
                    or stat.S_ISLNK(member.external_attr >> 16)):
                raise RuntimeError("Unsafe/duplicate ZIP member: " + name)
            if not member.is_dir():
                result[name] = archive.read(member)  # Checks the member CRC as well.
    return result


def json_bytes(record):
    return (json.dumps(record, indent=2) + "\n").encode()


def verify_payload(payload, records, image):
    nros = {name for name in payload if name.endswith(".nro")}
    expected = {f"switch/{app}/{app}.nro" for app in APPS}
    if nros != expected:
        raise RuntimeError("Incomplete or unexpected NRO inventory")
    for record in records:
        app = Path(record["name"]).stem
        raw = payload[f"switch/{app}/{app}.nro"]
        if sha(raw) != record["sha256"] or len(raw) != record["bytes"] or raw[16:20] != b"NRO0":
            raise RuntimeError("NRO hash/format mismatch: " + app)
    prefix = "switch/mc-runtime/"
    required = [prefix + "tests/" + name for name in TEST_JARS] + [
        prefix + "runtimes/minijvm/minijvm_rt.jar",
        prefix + "runtimes/openjdk25/lib/modules",
        prefix + "runtimes/openjdk25/lib/security/cacerts",
        prefix + "launchers/switchcraft-launcher-bridge.jar",
        prefix + "launchers/switchcraft-lwjgl-horizon.jar",
        prefix + "profiles/26.4-snapshot-6.json",
    ]
    if any(name not in payload for name in required):
        raise RuntimeError("Missing required runtime, smoke test or launcher resources")
    actual_image = {name for name in payload if name.startswith(prefix + "runtimes/openjdk25/")}
    if actual_image != {entry["path"] for entry in image}:
        raise RuntimeError("Incomplete Java 25 runtime image inventory")
    for entry in image:
        if sha(payload[entry["path"]]) != entry["sha256"]:
            raise RuntimeError("Java 25 runtime image hash mismatch: " + entry["path"])
    release = payload[prefix + "runtimes/openjdk25/release"].decode()
    if "java.base java.instrument" not in release:
        raise RuntimeError("Instrument-enabled Java 25 image required")
    for name in payload:
        if (name.startswith(("minecraft/", prefix + "logs/", prefix + "instances/"))
                or name in (prefix + "config/launcher.json", prefix + "config/launcher-ui.json")
                or PurePosixPath(name).name in ("accounts.json", "level.dat", "prod.keys", "title.keys")):
            raise RuntimeError("Refusing user data in the package: " + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=ROOT / "dist")
    parser.add_argument("--launcher", type=Path, default=ROOT / "dist/launcher-foundation")
    parser.add_argument("--output", type=Path, default=ROOT / "dist/complete-test-suite")
    args = parser.parse_args()
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip():
        raise RuntimeError("Commit the complete package recipe/documentation before packaging")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    epoch = int(subprocess.check_output(["git", "show", "-s", "--format=%ct", "HEAD"], cwd=ROOT))
    inputs = json.loads((ROOT / "config/test-suite-inputs.json").read_text())
    runtime = inputs["java_switch_revision"]
    base_path, base = load_input(args.base, "switch-minecraft-test-package.zip", inputs["base"], runtime)
    launcher_path, launcher = load_input(args.launcher, "switchcraft-launcher-foundation.zip", inputs["launcher"], runtime)
    payload = read_archive(base_path)
    payload.pop("manifest.json")
    payload.pop("INSTALL.txt")
    payload["switchcraft-base-e08f36a-source.tar.gz"] = payload.pop("switchcraft-corresponding-source.tar.gz")
    overlay = read_archive(launcher_path)
    overlay.pop("INSTALL-LAUNCHER.txt")
    overlay["switchcraft-launcher-13e9cff-source.tar.gz"] = overlay.pop("launcher-corresponding-source.tar.gz")
    payload.update(overlay)
    for name in DOCS:
        payload["switchcraft-docs/" + name] = (ROOT / "docs" / name).read_bytes()
    payload["switchcraft-docs/README.md"] = (ROOT / "README.md").read_bytes()
    payload["switchcraft-docs/collect-feedback.py"] = (ROOT / "tools/collect-feedback.py").read_bytes()
    guide = (ROOT / "docs/SD_TEST_PACKAGE.md").read_text()
    for name in DOCS:
        guide = guide.replace("](" + name + ")", "](switchcraft-docs/" + name + ")")
    payload["START_HERE.md"] = guide.encode()
    payload["INSTALL.txt"] = (
        "Extract this ZIP directly into the SD root, merging its contents.\n"
        "Expected: SD:/switch/java25-test/java25-test.nro (no wrapper directory).\n"
        "Keep the complete runtime, tests, sources and notices. Preserve personal configurations, saves and logs.\n"
        "Use application-mode hbmenu. Start with START_HERE.md.\n"
        "All Horizon execution is NOT TESTED; Minecraft cannot currently launch on Switch.\n"
    ).encode()
    source = subprocess.check_output(["git", "archive", "--format=tar", "--prefix=switchcraft/", revision], cwd=ROOT)
    payload["switchcraft-package-tools-source.tar.gz"] = gzip.compress(source, mtime=0)
    records = [record for record in base["artifacts"] if record["name"].endswith(".nro")
               and record["name"] != "minecraft-launcher.nro"]
    records.append(dict(launcher["launcher"], source_revision=launcher["source_revision"], java_switch_revision=runtime))
    verify_payload(payload, records, base["runtime_image_files"])
    # All JARs are unchanged built diagnostics/runtime helpers; no game payload is added.
    for entry in base["sd_resources"]:
        if sha(payload[entry["path"]]) != entry["sha256"]:
            raise RuntimeError("Diagnostic/runtime resource hash mismatch: " + entry["path"])
    manifest = {
        "project": "Switchcraft", "target": "26.4-snapshot-6", "package_id": inputs["package_id"],
        "package_kind": "Complete SD-root test suite", "packaging_revision": revision,
        "java_switch_revision": runtime, "sdk_abi": 1, "inputs": inputs, "artifacts": records,
        "hardware_verification": "NOT TESTED", "horizon_vm_java_jni_ffm_instrumentation": "NOT TESTED",
        "minecraft_title_on_horizon": "NOT ACHIEVED / NOT TESTED",
        "host_reference": launcher["host_minecraft_evidence"],
        "runtime_image_files": base["runtime_image_files"],
        "license_and_source": "Base e08f36a and launcher 13e9cff corresponding-source archives plus current package-tools source are included; notices are under switch/mc-runtime/licenses/.",
        "sd_files": [{"path": name, "bytes": len(raw), "sha256": sha(raw)} for name, raw in sorted(payload.items())],
    }
    payload["manifest.json"] = json_bytes(manifest)
    payload["switchcraft-docs/SD_FILES_SHA256SUMS"] = "".join(
        sha(raw) + "  " + name + "\n" for name, raw in sorted(payload.items())
    ).encode()
    args.output.mkdir(parents=True, exist_ok=True)
    output = args.output / "switchcraft-complete-test-suite-2026-11-08.zip"
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, raw in sorted(payload.items()):
            member = zipfile.ZipInfo(name, date_time=time.gmtime(epoch)[:6])
            member.compress_type = zipfile.ZIP_DEFLATED
            member.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(member, raw)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None or len(archive.namelist()) != len(payload):
            raise RuntimeError("Final ZIP integrity/inventory check failed")
        for name, raw in payload.items():
            if sha(archive.read(name)) != sha(raw):
                raise RuntimeError("Final ZIP member mismatch: " + name)
    manifest["archive"] = {"name": output.name, "bytes": output.stat().st_size, "sha256": file_sha(output)}
    external = args.output / "manifest.json"
    external.write_bytes(json_bytes(manifest))
    (args.output / "SHA256SUMS").write_text("".join(file_sha(p) + "  " + p.name + "\n" for p in (output, external)))
    print(json.dumps({"archive": manifest["archive"], "sd_files": len(payload), "nros": len(records),
                      "runtime_image_files": len(base["runtime_image_files"]), "hardware_verification": "NOT TESTED"}, indent=2))


if __name__ == "__main__":
    main()
