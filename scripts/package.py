#!/usr/bin/env python3
import datetime
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import tarfile
import zipfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
os.chdir(ROOT)
DIST=ROOT/"dist"
spec=importlib.util.spec_from_file_location("verify",ROOT/"scripts/verify-artifacts.py")
verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)
records=[verify.verify(DIST/(app+".nro"),ROOT/"build"/(app+".elf")) for app in verify.APPS]
revision=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
dirty=bool(subprocess.check_output(["git","status","--porcelain"],text=True).strip())
dk=pathlib.Path(os.environ.get("DEVKITPRO",str(ROOT/".toolchain/opt/devkitpro")))
compiler=subprocess.check_output([str(dk/"devkitA64/bin/aarch64-none-elf-gcc"),"--version"],text=True).splitlines()[0]
packages=sorted(p.name for p in (dk/"pacman/var/lib/pacman/local").glob('*') if p.is_dir())
toolchain={"image":json.loads((ROOT/"dependencies.lock.json").read_text())["toolchain_image"],"compiler":compiler,"packages":packages}
purposes={"switch-diagnostics.nro":"Controller menu, SD, process memory, native threads and NRO chaining",
    "opengl-test.nro":"Mesa NVC0 EGL, OpenGL strings/extensions, visible triangle and pixel readback",
    "vulkan-test.nro":"Experimental NVK enumeration, buffer fill/readback and offscreen triangle",
    "java-test.nro":"Interpreter-only miniJVM: original Java JAR diagnostic and static native bridge",
    "minecraft-launcher.nro":"Read-only Minecraft metadata inspection, isolated launch planning and settings"}
limitations=["All Horizon hardware execution NOT TESTED","Minecraft client not launched on Horizon; host bootstrap failed before rendering",
    "Vulkan WSI/swapchain presentation not implemented","miniJVM is not OpenJDK and does not provide standard JNI Invocation API",
    "No LWJGL, OpenAL, Fabric or Microsoft authentication integration","NVK driver comes from a hash-pinned prebuilt archive; exact nxvk source commit was not provided by upstream release"]
bundled={
    "switch-diagnostics.nro":["libnx 4.12.0", "newlib 4.6.0.20260123"],
    "opengl-test.nro":["libnx 4.12.0", "newlib", "Mesa NVC0/EGL 20.1.0-5", "GLAD 0.1.27", "Nouveau portlib", "libstdc++"],
    "vulkan-test.nro":["libnx 4.12.0", "newlib", "Mesa NVK 25.0.7 public archive", "bundled Expat/nxvk compatibility and Rust support", "Nouveau portlib", "libstdc++"],
    "java-test.nro":["libnx 4.12.0", "newlib", "miniJVM 87c9808 interpreter and Horizon patch", "bundled miniz/tinycthread/mbedTLS", "external SD miniJVM GPL Java class library"],
    "minecraft-launcher.nro":["libnx 4.12.0", "newlib", "nlohmann JSON 3.11.3", "libstdc++"]}
for item in records:
    item.update(purpose=purposes[item["name"]],source_revision=revision,source_dirty=dirty,
                build_date=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                toolchain=toolchain,bundled_dependencies=bundled[item["name"]],
                tested_environment="Linux cross-build and host tests; no Horizon execution",known_limitations=limitations)
sd=DIST/"COPY_TO_SD"
if sd.exists():shutil.rmtree(sd)
for app in verify.APPS:
    dest=sd/"switch"/app;dest.mkdir(parents=True);shutil.copyfile(DIST/(app+".nro"),dest/(app+".nro"))
runtime=sd/"switch/mc-runtime"
for sub in ["config","logs","runtimes/minijvm","tests","instances/java-smoke","tmp","licenses"]:(runtime/sub).mkdir(parents=True,exist_ok=True)
for sub in ["versions","libraries","assets","mods","config","saves","resourcepacks","shaderpacks"]:(sd/"minecraft/.minecraft"/sub).mkdir(parents=True,exist_ok=True)
shutil.copyfile(ROOT/"build/minijvm_rt.jar",runtime/"runtimes/minijvm/minijvm_rt.jar")
for name in ["diagnostic-tests.jar","dependency.jar"]:shutil.copyfile(ROOT/"build"/name,runtime/"tests"/name)
shutil.copyfile(ROOT/"config/launcher.example.json",runtime/"config/launcher.example.json")
for file in (ROOT/"licenses").rglob('*'):
    if file.is_file():
        dest=runtime/"licenses"/file.relative_to(ROOT/"licenses");dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,dest)
shutil.copyfile(ROOT/"LICENSE",runtime/"licenses/SWITCHCRAFT-MIT.txt")
shutil.copyfile(ROOT/"vendor/JSON-LICENSE.MIT",runtime/"licenses/NLOHMANN-JSON-MIT.txt")
for file in ["README.md","docs/TEST_PLAN.md","docs/KNOWN_ISSUES.md"]:
    dest=sd/"switchcraft-docs"/pathlib.Path(file).name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/file,dest)
(sd/"INSTALL.txt").write_text("Copy switch/ and minecraft/ to the SD root; merge directories, preserve saves and existing configuration.\nStart switch-diagnostics in application-mode hbmenu. All hardware tests are NOT TESTED.\nRead switchcraft-docs/TEST_PLAN.md. No game files are included.\n")
# Corresponding source accompanies the GPL class library. Include all Java
# sources, native modifications, build scripts and source repository snapshot.
source=DIST/"switchcraft-corresponding-source.tar.gz"
with tarfile.open(source,"w:gz") as tar:
    tracked=subprocess.check_output(["git","ls-files","-z"]).split(b'\0')
    for name in tracked:
        if name:tar.add(ROOT/os.fsdecode(name),arcname="switchcraft/"+os.fsdecode(name))
    tar.add(ROOT/".deps/minijvm-source",arcname="third_party/minijvm-source")
    tar.add(ROOT/".deps/minijvm",arcname="third_party/minijvm-horizon-c")
shutil.copyfile(source,sd/"switchcraft-corresponding-source.tar.gz")
manifest={"project":"Switchcraft","source_revision":revision,"source_dirty":dirty,"hardware_verification":"NOT TESTED",
    "artifacts":records,"not_produced":{"minecraft-aot-test.nro":"Unavailable external pz-switch runtime, GraalVM image and legitimately supplied patched game inputs"},
    "known_limitations":limitations,"dependency_lock":json.loads((ROOT/"dependencies.lock.json").read_text()),
    "package_manifest_note":"The manifest inside the ZIP describes NROs/resources. This external manifest additionally hashes the final ZIP to avoid a circular hash."}
manifest["sd_resources"]=[]
for file in sorted(runtime.rglob('*.jar')):
    manifest["sd_resources"].append({"path":file.relative_to(sd).as_posix(),"bytes":file.stat().st_size,"sha256":hashlib.sha256(file.read_bytes()).hexdigest()})
(DIST/"manifest.json").write_text(json.dumps(manifest,indent=2)+'\n')
shutil.copyfile(DIST/"manifest.json",sd/"manifest.json")
archive=DIST/"switch-minecraft-test-package.zip"
with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as zip:
    for file in sorted(sd.rglob('*')):
        if file.is_file():zip.write(file,file.relative_to(sd))
        elif not any(file.iterdir()):zip.writestr(file.relative_to(sd).as_posix()+'/',b'')
for file,purpose in [(archive,"Installable SD test package"),(source,"Project and miniJVM Java/C corresponding source")]:
    manifest["artifacts"].append({"name":file.name,"purpose":purpose,"source_revision":revision,"source_dirty":dirty,
        "build_date":datetime.datetime.now(datetime.timezone.utc).isoformat(),"toolchain":toolchain,
        "bundled_dependencies":(["Five native applications", "miniJVM Java class library and original diagnostic JARs", "licenses and source"] if file==archive else ["Original project source", "complete miniJVM Java source", "modified miniJVM C source", "build scripts and licenses"]),
        "build_verification":"PASS","tested_environment":"Archive generation and host checksum/ZIP validation", "hardware_verification":"NOT TESTED",
        "known_limitations":limitations,"bytes":file.stat().st_size,"sha256":hashlib.sha256(file.read_bytes()).hexdigest()})
(DIST/"manifest.json").write_text(json.dumps(manifest,indent=2)+'\n')
test_log=(ROOT/"build/host-tests.log").read_text() if (ROOT/"build/host-tests.log").exists() else ""
test_match=re.search(r"Ran (\d+) tests",test_log)
tests=test_match.group(1)+" host tests passed" if test_match and re.search(r"\nOK\s*$",test_log) else "Host test status: consult build/host-tests.log"
report=f'''# Switchcraft delivery report

## A. Implemented functionality

Five Horizon-native applications: platform/SD/memory/controller/thread diagnostics;
Mesa NVC0 EGL/OpenGL visible triangle and pixel readback; NVK device/queue/heap
enumeration, GPU transfer and offscreen triangle; miniJVM interpreter with real
Java 8 JAR tests and custom static native bridge; read-only Minecraft version
inspection, inherited metadata, classpath/argument planning and saved settings.
Minecraft is not playable. All Horizon execution remains NOT TESTED.

## B. Deliverable artifacts

Source revision: `{revision}`. Tracked/untracked source modifications at package
time: `{dirty}`. Paths below are relative to `{DIST}`.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
'''
for item in manifest["artifacts"]:report+=f'| `{item["name"]}` | {item["bytes"]} | `{item["sha256"]}` |\n'
report+=f'''
The extracted install layout is `dist/COPY_TO_SD/`. `dist/SHA256SUMS` also
covers the manifest and this report. No placeholder AOT binary is present.

## C. Build validation

All five NROs linked successfully using `{compiler}` and libnx 4.12.0 from
the digest-pinned toolchain. NRO0/ASET, segment ranges, NACP identity/version,
JPEG icon, AArch64 ELF and matching build IDs pass validation. {tests}.
The real interpreter suite covers JAR loading, arithmetic, exceptions, reflection,
threads, allocation, file I/O, static native calls and shutdown. It does not test
standard JNI Invocation. Failed OpenJDK, AOT and initial build experiments are
preserved under `docs/evidence/`.

## D. Hardware testing

NOT TESTED: all controller/SD/memory/thread/JVM/GL/Vulkan execution on Horizon.
No physical Switch was attached. No title screen, world, frame rate, usable game
heap or Mod compatibility has been established.

## E. Installation

Merge the ZIP's `switch/` and `minecraft/` folders onto the SD root; retain saves
and real configuration. The ZIP contains no game files or real launcher.json.
Start switch-diagnostics through application-mode hbmenu on Atmosphère. To inspect
an existing legitimate installation, copy its versions/libraries/assets into
sdmc:/minecraft/.minecraft or set another root in mc-runtime/config/launcher.json.
The inspector only writes runtime settings/logs, not that installation.

## F. First three hardware sessions

1. Run native menu/input, SD, memory and thread tests (HW-01 through HW-05).
2. Run OpenGL context, visible triangle, pixel readback and restoration (HW-06/07).
3. Run NVK enumeration, then buffer fill/readback (HW-08/09); only afterward try
   the offscreen triangle and Java suite. Export all mc-runtime/logs afterward.

The full case-by-case plan and fillable result sheet are `docs/TEST_PLAN.md`.

## G. Architecture

See `docs/ARCHITECTURE.md` (Mermaid) and `docs/architecture.svg`. Solid paths are
implemented; dashed paths are future JVM/LWJGL/game/WSI work. The SD layout keeps
standard .minecraft content separate from runtime binaries/configuration/logs.

## H. Known limitations

OpenJDK and standard JNI Invocation are absent. miniJVM's incomplete Java 8 class
library fails the isolated host Minecraft 1.12.2 attempt at missing APIs/AWT/LWJGL,
ending in IncompatibleClassChangeError in Main.main before rendering. No fabricated
authentication arguments were supplied. Modern Java 17/21/25 clients are metadata
targets only. Vulkan presentation, Zink, LWJGL/GLFW/OpenAL, audio, authentication
and Fabric/Mixin are unfinished. The Java heap target does not cap all native
allocations. AOT needs missing external pz-switch/GraalVM/user game inputs.
See `docs/KNOWN_ISSUES.md` and `docs/COMPATIBILITY.md`.

## I. Next steps

Collect hardware logs, repair any platform failures, add Vulkan WSI, reconstruct
a self-contained OpenJDK port and integrate a small JNI/LWJGL bridge before
attempting a game title screen. Preserve working diagnostic baselines; introduce
Fabric only after actual runtime transformation and a real Mod test.

## J. Source changes and commits

The originally empty repository now contains native apps/platform adapters,
portable metadata code, the reviewed miniJVM patch, original Java tests, host
tests, hash-locked dependencies, build/package/verification scripts, CI/Docker
definitions and English engineering/hardware documentation. Original code is MIT;
third-party licenses and full miniJVM Java/C source accompany the package.
Exact compiler/dependency versions are in manifest.json and dependencies.lock.json.

```
'''
report+=subprocess.check_output(["git","log","--oneline","-12"],text=True)+"```\n"
(DIST/"DELIVERY_REPORT.md").write_text(report)
checks=[]
for file in sorted(DIST.iterdir()):
    if file.is_file() and file.name!="SHA256SUMS":checks.append(hashlib.sha256(file.read_bytes()).hexdigest()+"  "+file.name)
(DIST/"SHA256SUMS").write_text('\n'.join(checks)+'\n')
print("Packaged",len(verify.APPS),"verified NROs:",archive)
