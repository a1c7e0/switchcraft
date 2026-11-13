#!/usr/bin/env python3
"""Package only the verified SD runtime and diagnostic applications for R4."""
import argparse
import hashlib
import io
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
TAG = "test-suite-2026-11-12-r4"
ARCHIVE_NAME = "switchcraft-test-suite-2026-11-12-r4.zip"
SOURCE_NAME = "switchcraft-source-2026-11-12-r4.tar.gz"


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
    if manifest.get("release_tag") != TAG:
        raise RuntimeError("Fresh SD manifest does not identify the R4 release tag")
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
    runtime_image = manifest.get("runtime_image_files", [])
    expected_profile_modules = set(source_lock["java_switch"].get("runtime_image_modules", []))
    if (len(expected_profile_modules) != 10 or
            not {"java.base", "java.instrument"} <= expected_profile_modules):
        raise RuntimeError("dependencies.lock.json must pin the ten-module Java 25 Minecraft profile")
    if (not isinstance(runtime_image, list) or not runtime_image or
            manifest.get("runtime_minecraft_profile") is not True or
            not isinstance(manifest.get("runtime_image_modules"), list) or
            set(manifest["runtime_image_modules"]) != expected_profile_modules):
        raise RuntimeError("Fresh manifest has no verified full Minecraft Java module profile")
    runtime_paths = [item.get("path") for item in runtime_image]
    if (len(runtime_paths) != len(set(runtime_paths)) or
            "switch/mc-runtime/runtimes/openjdk25/lib/modules" not in runtime_paths or
            "switch/mc-runtime/runtimes/openjdk25/lib/security/cacerts" not in runtime_paths):
        raise RuntimeError("Fresh manifest has no Java module image inventory")
    jar_inventory = manifest.get("runtime_and_test_jars", [])
    if (not isinstance(jar_inventory, list) or not jar_inventory or
            len({entry.get("path") for entry in jar_inventory}) != len(jar_inventory)):
        raise RuntimeError("Fresh manifest has no runtime/test JAR inventory")
    source_path = ROOT / "dist" / SOURCE_NAME
    source_record = next((entry for entry in manifest.get("artifacts", [])
                          if entry["name"] == SOURCE_NAME), None)
    if (source_record is None or not source_path.is_file() or
            sha_file(source_path) != source_record["sha256"]):
        raise RuntimeError("Matching R4 source companion is missing or differs from the fresh build manifest")

    selected = {}
    expected_nros = {f"switch/{app}/{app}.nro" for app in APPS}
    artifact_records = {record["name"]: record for record in manifest["artifacts"]
                        if record["name"].endswith(".nro")}
    if {f"{app}.nro" for app in APPS} != set(artifact_records):
        raise RuntimeError("Manifest NRO inventory does not match the nine required applications")
    records_by_path = {entry["path"]: entry for entry in manifest["sd_resources"]}
    records_by_path.update({entry["path"]: entry for entry in runtime_image})
    if len(records_by_path) != len(manifest["sd_resources"]) + len(runtime_image):
        raise RuntimeError("Duplicate runtime resource paths in manifest")
    for record in runtime_image:
        safe_relative(record["path"])
        if not isinstance(record.get("sha256"), str) or len(record["sha256"]) != 64:
            raise RuntimeError("Invalid runtime image hash record: " + str(record.get("path")))
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
    expected_jars = {entry["path"] for entry in jar_inventory}
    if jars != expected_jars:
        raise RuntimeError("Runtime/test JAR files differ from the manifest inventory")
    for entry in jar_inventory:
        safe_relative(entry["path"])
        if not entry["path"].startswith("switch/mc-runtime/") or not entry["path"].endswith(".jar"):
            raise RuntimeError("Invalid runtime/test JAR path: " + entry["path"])
        if entry.get("sha256") != digest(selected[entry["path"]]):
            raise RuntimeError("Runtime/test JAR hash differs from inventory: " + entry["path"])
    core_jar = "switch/mc-runtime/libraries/lwjgl-3.4.3.jar"
    core_record = next((entry for entry in manifest["sd_resources"] if entry["path"] == core_jar), None)
    core_lock = json.loads((ROOT / "dependencies.lock.json").read_text())["lwjgl_core"]
    if core_record is None or core_record["sha256"] != core_lock["sha256"]:
        raise RuntimeError("The installed LWJGL 3.4.3 core JAR is missing or differs from the pinned artifact")
    if set(name for name in selected if name.endswith(".nro")) != expected_nros:
        raise RuntimeError("Final payload does not contain exactly the nine required NROs")
    if any(not (name.startswith("switch/") or name in {"README.md", "START_HERE.md"})
           for name in selected):
        raise RuntimeError("SD package contains content outside switch/ and its short instructions")
    for name in jars:
        with zipfile.ZipFile(io.BytesIO(selected[name])) as archive:
            members = archive.namelist()
            if any(member.lower().endswith((".so", ".dll", ".dylib")) for member in members):
                raise RuntimeError("Host-native library is forbidden in the SD package: " + name)
            if any("natives-linux" in member.lower() or "natives-windows" in member.lower() or
                   "natives-macos" in member.lower() for member in members):
                raise RuntimeError("Host-native JAR is forbidden in the SD package: " + name)

    # A compact README and START_HERE are the only non-switch payload files.
    release_url = f"https://github.com/a1c7e0/switchcraft/releases/download/{TAG}"
    readme = ("# Switchcraft device test package\n\n"
              f"Download and extract [{ARCHIVE_NAME}]({release_url}/{ARCHIVE_NAME}) directly into the SD root, "
              "merging files and preserving existing saves and configuration. Use application-mode "
              "hbmenu. Start with START_HERE.md and report results as PASS, FAIL or NOT TESTED.\n\n"
              f"For licensing and reproducibility, the matching source companion is "
              f"[{SOURCE_NAME}]({release_url}/{SOURCE_NAME}). Hardware execution is not established by this package.\n")
    selected["README.md"] = readme.encode()
    selected["START_HERE.md"] = (
        "# Switchcraft R4 device test package\n\n"
        f"Extract this ZIP directly into the SD root: [download the package]({release_url}/{ARCHIVE_NAME}). "
        "Merge folders and preserve existing saves/configuration. Use Switch 1, Atmosphere, "
        "and application-mode hbmenu. The required applications are under switch/.\n\n"
        "## Focused R4 device run\n\n"
        "Before starting, record Switch firmware, Atmosphere and hbmenu versions. For every "
        "Java 25 attempt, launch a fresh application-mode hbmenu process and start only one "
        "test. Let its result screen finish, close the app normally with +, then close and "
        "reopen hbmenu before the next attempt. Record the approximate wait time and result.\n\n"
        "| Order | App and action | Continue when |\n"
        "| --- | --- | --- |\n"
        "| 1 | Fresh `java25-test`, A | Continue only if the result shows `Hello from Horizon Java 25`. |\n"
        "| 2 | Fresh `java25-test`, X | Run only after A passes; record the JNI/FFM suite result. |\n"
        "| 3 | Fresh `java25-test`, Y | Run only after X passes; record the startup-agent result. |\n"
        "| 4 | Fresh `switchcraft-java25`, A | Run after standalone A/X/Y pass; record the combined Hello result. |\n"
        "| 5 | Fresh `switchcraft-java25`, X | Run only after combined A passes; record the SDL JNI/FFM result. |\n"
        "| 6 | Fresh `switchcraft-java25`, Y | Run only after combined X passes; record LWJGL core, SDL, and Vulkan FFM markers/results. |\n"
        "| 7 | Fresh `switchcraft-java25`, B | After standalone and combined A/X/Y pass; require `PRESENTATION_PASS frames=60` and VMA allocator init/destroy. |\n"
        "| 8 | Fresh `switchcraft-java25`, R | After the same prerequisites; require FreeType and OpenAL loopback pass markers. No physical audio output is tested. |\n"
        "| 9 | Fresh `switchcraft-java25`, L | After the same prerequisites; require STB PNG, shaderc, SPIR-V Cross and utilities pass markers. |\n"
        "| Optional | `zero-services-test`, L | This diagnostic was reported unable to start in R3 without a supplied log; record it separately and do not block Java A. |\n\n"
        "Use a new application process for every row. If a prerequisite fails, leave dependent actions untested. After the attempts, export "
        "all logs and unique tick-named VM captures. `java25-test.log` may append across runs, "
        "so preserve each attempt's stdout/stderr capture. The collector below exports its "
        "allowlisted logs, including `hs_err_pid*.log` in the two Java 25 app folders. "
        "Review and attach Atmosphere/system crash reports separately if present. "
        "Cross-builds and host results are not device passes.\n\n"
        "For licensing and reproducibility, download the matching separate source companion "
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
        "zero_services_launch_observation": "R3 reported unable to start; no log or crash capture supplied; cause unresolved. R4 stack hardening and main-entry marker are not a demonstrated startup fix.",
        "combined_y_scope": "Cross-built LWJGL core JNI plus SDL/Vulkan FFM diagnostic; device execution NOT TESTED.",
        "runtime_image_files": runtime_image,
        "runtime_image_modules": manifest["runtime_image_modules"],
        "runtime_minecraft_profile": manifest["runtime_minecraft_profile"],
        "applications": [{"name": app, "path": f"switch/{app}/{app}.nro",
                           "sha256": digest(selected[f"switch/{app}/{app}.nro"]),
                           "build_id": artifact_records[app + ".nro"]["build_id"],
                           "source_repository": artifact_records[app + ".nro"]["source_repository"],
                           "source_revision": artifact_records[app + ".nro"]["source_revision"]}
                          for app in APPS],
        "runtime_and_test_jar_count": len(jar_inventory),
        "runtime_and_test_jars": jar_inventory,
        "source_archive": {"name": SOURCE_NAME, "bytes": source_record["bytes"],
                           "sha256": source_record["sha256"],
                           "lwjgl_upstream_sha256": source_lock["lwjgl_core"]["source_archive_sha256"],
                           "components": manifest.get("source_companions", []),
                           "licenses": manifest.get("source_licenses", [])},
        "source_archive_notice": "Required separate matching release asset for licensing and reproducibility; not included in the SD ZIP.",
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
                      "runtime_image_files": len(runtime_image),
                      "hardware_verification": "NOT TESTED"}, indent=2))


if __name__ == "__main__":
    main()
