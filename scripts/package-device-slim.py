#!/usr/bin/env python3
"""Package only the verified SD runtime and diagnostic applications for R3."""
import argparse
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
EXPECTED_JARS = 10
TAG = "test-suite-2026-11-09-r3"
ARCHIVE_NAME = "switchcraft-test-suite-2026-11-09-r3.zip"
SOURCE_NAME = "switchcraft-source-2026-11-09-r3.tar.gz"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def safe_relative(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name or str(path) != name:
        raise RuntimeError("Unsafe SD path in manifest: " + name)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sd-root", type=Path, default=ROOT / "dist/COPY_TO_SD",
                        help="fresh verified SD-root tree from scripts/package.py")
    parser.add_argument("--manifest", type=Path, default=ROOT / "dist/manifest.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist/device-test-slim")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text())
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip():
        raise RuntimeError("Commit the package recipe and source before producing a release ZIP")
    source_revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if manifest.get("source_revision") != source_revision:
        raise RuntimeError("Fresh SD build manifest does not match the clean source commit")
    if manifest.get("source_dirty") is not False:
        raise RuntimeError("Refusing a dirty or unverified source build")
    runtime_revision = manifest.get("java_switch_revision", "")
    if len(runtime_revision) != 40 or any(ch not in "0123456789abcdef" for ch in runtime_revision):
        raise RuntimeError("Runtime manifest must identify an immutable full commit pin")
    source_lock = json.loads((ROOT / "dependencies.lock.json").read_text())
    if runtime_revision != source_lock["java_switch"]["revision"]:
        raise RuntimeError("Built Java Switch runtime differs from dependencies.lock.json")
    if manifest.get("dependency_lock", {}).get("java_switch", {}).get("revision") != runtime_revision:
        raise RuntimeError("Built manifest's Java Switch lock differs from its runtime image")
    if len(manifest.get("runtime_image_files", [])) != 39:
        raise RuntimeError("Expected all 39 verified Java 25 image files")
    if len(manifest.get("sd_resources", [])) != EXPECTED_JARS:
        raise RuntimeError("Expected all ten verified runtime and test JARs")

    selected = {}
    expected_nros = {f"switch/{app}/{app}.nro" for app in APPS}
    artifact_records = {record["name"]: record for record in manifest["artifacts"]
                        if record["name"].endswith(".nro")}
    if {f"{app}.nro" for app in APPS} != set(artifact_records):
        raise RuntimeError("Manifest NRO inventory does not match the nine required applications")
    records_by_path = {entry["path"]: entry for entry in manifest["sd_resources"]}
    records_by_path.update({entry["path"]: entry for entry in manifest["runtime_image_files"]})
    if len(records_by_path) != len(manifest["sd_resources"]) + len(manifest["runtime_image_files"]):
        raise RuntimeError("Duplicate runtime resource paths in manifest")
    for record in manifest["runtime_image_files"]:
        safe_relative(record["path"])
    for record in manifest["sd_resources"]:
        safe_relative(record["path"])

    for relative in sorted(expected_nros):
        source = args.sd_root / relative
        app = PurePosixPath(relative).parent.name
        record = artifact_records[app + ".nro"]
        data = source.read_bytes()
        if digest(data) != record["sha256"] or len(data) != record["bytes"] or data[16:20] != b"NRO0":
            raise RuntimeError("NRO does not match verified manifest: " + relative)
        selected[relative] = data

    for relative, record in records_by_path.items():
        data = (args.sd_root / relative).read_bytes()
        if digest(data) != record["sha256"] or ("bytes" in record and len(data) != record["bytes"]):
            raise RuntimeError("Runtime file does not match verified manifest: " + relative)
        selected[relative] = data

    licenses = args.sd_root / "switch/mc-runtime/licenses"
    for path in sorted(licenses.rglob("*")):
        if path.is_symlink():
            raise RuntimeError("Refusing symlink in license directory: " + str(path))
        if path.is_file():
            relative = path.relative_to(args.sd_root).as_posix()
            selected[relative] = path.read_bytes()
    if not any(name.startswith("switch/mc-runtime/licenses/") for name in selected):
        raise RuntimeError("No embedded license texts found")

    jars = {name for name in selected if name.startswith("switch/mc-runtime/") and name.endswith(".jar")}
    if len(jars) != EXPECTED_JARS:
        raise RuntimeError(f"Expected exactly ten runtime/test JARs, found {len(jars)}")
    if set(name for name in selected if name.endswith(".nro")) != expected_nros:
        raise RuntimeError("Final payload does not contain exactly the nine required NROs")

    # A compact README and START_HERE are the only non-switch payload files.
    release_url = f"https://github.com/a1c7e0/switchcraft/releases/download/{TAG}"
    readme = ("# Switchcraft device test package\n\n"
              f"Download and extract [{ARCHIVE_NAME}]({release_url}/{ARCHIVE_NAME}) directly into the SD root, "
              "merging files and preserving existing saves and configuration. Use application-mode "
              "hbmenu. Start with START_HERE.md and report results as PASS, FAIL or NOT TESTED.\n\n"
              f"For licensing and reproducibility, the matching optional source archive is "
              f"[{SOURCE_NAME}]({release_url}/{SOURCE_NAME}). Hardware execution is not established by this package.\n")
    selected["README.md"] = readme.encode()
    selected["START_HERE.md"] = (
        "# Switchcraft R3 device test package\n\n"
        f"Extract this ZIP directly into the SD root: [download the package]({release_url}/{ARCHIVE_NAME}). "
        "Merge folders and preserve existing saves/configuration. Use Switch 1, Atmosphere, "
        "and application-mode hbmenu. The required applications are under switch/.\n\n"
        "## Focused R3 retest\n\n"
        "Before starting, record Switch firmware, Atmosphere and hbmenu versions. For every "
        "Java 25 attempt, launch a fresh application-mode hbmenu process and start only one "
        "test. Let its result screen finish, close the app normally with +, then close and "
        "reopen hbmenu before the next attempt. Record the approximate wait time and result.\n\n"
        "| Order | App and action | Continue when |\n"
        "| --- | --- | --- |\n"
        "| 1 | `zero-services-test`, L | Record the new guard and committed-range checks, raw statuses/results, and canary outcome. Do this first. |\n"
        "| 2 | Fresh `java25-test`, A | Continue only if the result shows `Hello from Horizon Java 25`. |\n"
        "| 3 | Fresh `java25-test`, X | Run only after A passes; record the JNI/FFM suite result. |\n"
        "| 4 | Fresh `java25-test`, Y | Run only after X passes; record the startup-agent result. |\n"
        "| 5 | Fresh `switchcraft-java25`, A | Run after standalone A/X/Y pass; record the combined Hello result. |\n"
        "| 6 | Fresh `switchcraft-java25`, X | Run only after combined A passes; record the SDL JNI/FFM result. |\n\n"
        "If a prerequisite fails, leave dependent actions untested. After the attempts, export "
        "all logs and unique tick-named VM captures. `java25-test.log` may append across runs, "
        "so preserve each attempt's stdout/stderr capture. The collector below exports its "
        "allowlisted logs, including `hs_err_pid*.log` in the two Java 25 app folders. "
        "Review and attach Atmosphere/system crash reports separately if present. "
        "Cross-builds and host results are not device passes.\n\n"
        "For licensing and reproducibility, download the matching optional source archive "
        f"[{SOURCE_NAME}]({release_url}/{SOURCE_NAME}). To export allowed diagnostic logs, run "
        "`python3 switch/mc-runtime/tools/collect-feedback.py --sd-root /path/to/SD "
        "--output ./switchcraft-feedback.zip` on a PC; choose an output path outside the SD card.\n"
    ).encode()
    selected["switch/mc-runtime/tools/collect-feedback.py"] = (ROOT / "tools/collect-feedback.py").read_bytes()

    runtime_revision = manifest["java_switch_revision"]
    records = [{"path": name, "bytes": len(data), "sha256": digest(data)}
               for name, data in sorted(selected.items())]
    package_manifest = {
        "project": "Switchcraft", "target": manifest["target"], "release_tag": TAG,
        "package_id": TAG, "package_kind": "Minimal SD-root device test package",
        "source_revision": source_revision, "java_switch_revision": runtime_revision,
        "sdk_abi": 1, "hardware_verification": "NOT TESTED",
        "horizon_vm_java_jni_ffm_instrumentation": "NOT TESTED",
        "minecraft_title_on_horizon": "NOT ACHIEVED / NOT TESTED",
        "runtime_image_files": manifest["runtime_image_files"],
        "applications": [{"name": app, "path": f"switch/{app}/{app}.nro",
                           "sha256": digest(selected[f"switch/{app}/{app}.nro"]),
                           "build_id": artifact_records[app + ".nro"]["build_id"],
                           "source_repository": artifact_records[app + ".nro"]["source_repository"],
                           "source_revision": artifact_records[app + ".nro"]["source_revision"]}
                          for app in APPS],
        "runtime_and_test_jar_count": EXPECTED_JARS,
        "source_archive": SOURCE_NAME,
        "source_archive_notice": "Optional separate release asset for licensing and reproducibility.",
        "input_manifest_sha256": sha_file(args.manifest),
        "sd_files": records,
    }
    selected["manifest.json"] = (json.dumps(package_manifest, indent=2) + "\n").encode()
    sums = "".join(digest(data) + "  " + name + "\n" for name, data in sorted(selected.items()))
    selected["switch/mc-runtime/SD_FILES_SHA256SUMS"] = sums.encode()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / ARCHIVE_NAME
    epoch = int(subprocess.check_output(["git", "show", "-s", "--format=%ct", "HEAD"], cwd=ROOT))
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in sorted(selected.items()):
            member = zipfile.ZipInfo(name, date_time=time.gmtime(epoch)[:6])
            member.compress_type = zipfile.ZIP_DEFLATED
            member.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(member, data)

    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None or set(archive.namelist()) != set(selected):
            raise RuntimeError("ZIP integrity or inventory validation failed")
        for name, data in selected.items():
            if digest(archive.read(name)) != digest(data):
                raise RuntimeError("ZIP content verification failed: " + name)
        names = set(archive.namelist())
        if any(name.startswith(("switchcraft-docs/", "minecraft/")) for name in names):
            raise RuntimeError("Unexpected documentation tree or game payload in ZIP")
        if any(name.endswith((".o", ".a", ".elf", ".debug")) for name in names):
            raise RuntimeError("Debug/build products are not allowed in the SD package")
    package_manifest["archive"] = {"name": output.name, "bytes": output.stat().st_size,
                                   "sha256": sha_file(output)}
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(package_manifest, indent=2) + "\n")
    (args.output_dir / "SHA256SUMS").write_text(
        f"{sha_file(output)}  {output.name}\n{sha_file(manifest_path)}  {manifest_path.name}\n")
    print(json.dumps({"archive": package_manifest["archive"], "sd_files": len(selected),
                      "nros": len(expected_nros), "jars": len(jars),
                      "runtime_image_files": len(manifest["runtime_image_files"]),
                      "hardware_verification": "NOT TESTED"}, indent=2))


if __name__ == "__main__":
    main()
