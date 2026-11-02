#!/usr/bin/env python3
import datetime
import hashlib
import importlib.util
import json
import os
import pathlib
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
limitations=["All Horizon hardware execution NOT TESTED","Minecraft client not launched",
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
        "bundled_dependencies":["Five native applications", "miniJVM Java class library and original diagnostic JARs", "licenses and source"],
        "build_verification":"PASS","tested_environment":"Archive generation and host checksum/ZIP validation", "hardware_verification":"NOT TESTED",
        "known_limitations":limitations,"bytes":file.stat().st_size,"sha256":hashlib.sha256(file.read_bytes()).hexdigest()})
(DIST/"manifest.json").write_text(json.dumps(manifest,indent=2)+'\n')
checks=[]
for file in sorted(DIST.iterdir()):
    if file.is_file() and file.name!="SHA256SUMS":checks.append(hashlib.sha256(file.read_bytes()).hexdigest()+"  "+file.name)
(DIST/"SHA256SUMS").write_text('\n'.join(checks)+'\n')
print("Packaged",len(records),"verified NROs:",archive)
