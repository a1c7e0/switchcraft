#!/usr/bin/env python3
"""Package the pinned snapshot-6 native bring-up without shipping game files."""
import datetime,hashlib,importlib.util,io,json,os,pathlib,shutil,subprocess,tarfile,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1];os.chdir(ROOT);DIST=ROOT/'dist'
LOCK=json.loads((ROOT/'dependencies.lock.json').read_text())
JAVA=pathlib.Path(os.environ.get('JAVA_SWITCH_SOURCE',str(ROOT/'.deps/java-switch')))
spec=importlib.util.spec_from_file_location('verify',ROOT/'scripts/verify-artifacts.py');verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)
records=[verify.verify(DIST/(app+'.nro'),ROOT/'build'/(app+'.elf')) for app in verify.APPS]
revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
java_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=JAVA,text=True).strip()
assert java_revision==LOCK['java_switch']['revision']
dirty=bool(subprocess.check_output(['git','status','--porcelain'],text=True).strip())
assert not dirty, 'Commit the complete source before packaging'
dk=pathlib.Path(os.environ.get('DEVKITPRO',str(ROOT/'.toolchain/opt/devkitpro')))
toolchain={'image':LOCK['toolchain_image'],'compiler':subprocess.check_output([str(dk/'devkitA64/bin/aarch64-none-elf-gcc'),'--version'],text=True).splitlines()[0],
    'packages':sorted(p.name for p in (dk/'pacman/var/lib/pacman/local').glob('*') if p.is_dir())}
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
limitations=['Horizon execution NOT TESTED','Java 25 Zero VM cross-linked in diagnostic NROs; startup and execution unverified; no Minecraft title on Switch',
    'Host-only strict Vulkan demo title verified; this is not a Horizon result','NVK Maxwell is experimental/nonconformant',
    'SDL3/VI presentation and libffi W^X closures compiled, awaiting physical tests','LWJGL static native loading, shaderc/VMA/SPIR-V Cross/audio bindings not integrated into a Horizon JVM',
    'Fabric, account authentication and arbitrary Mods not implemented']
purposes={'switch-diagnostics.nro':'Native memory, SD, input, threads and next-load menu',
 'vulkan-test.nro':'NVK transfer/readback and offscreen triangle',
 'vulkan-present.nro':'Exact snapshot-6 base features, SDL3 gamepad/window and VI swapchain presentation',
 'minecraft-launcher.nro':'Read-only instance planning, strict Vulkan arguments and explicit Java-25 runtime gate',
 'java-test.nro':'Independent java-switch Java-8 interpreter diagnostic; not a Java-25 VM',
 'ffi-test.nro':'AAPCS64 downcalls, libnx W^X upcalls and whole-region memory probe',
 'zero-services-test.nro':'Standalone OpenJDK native service diagnostic, without a VM',
 'java25-test.nro':'Independent genuine Java 25 VM A/X/Y diagnostic; Horizon startup untested',
 'switchcraft-java25.nro':'Genuine Java 25 Hello and JNI/FFM SDL version diagnostics with composed provider; Horizon startup untested'}
for item in records:
    external=item['name'] in ['java-test.nro','ffi-test.nro','zero-services-test.nro','java25-test.nro']
    item.update(source_repository='a1c7e0/java-switch' if external else 'a1c7e0/switchcraft', switchcraft_integration_revision=revision)
    item.update(purpose=purposes[item['name']],source_revision=java_revision if external else revision,java_switch_revision=java_revision,source_dirty=dirty,build_date=now,toolchain=toolchain,
        bundled_dependencies=['libnx/newlib', 'Pinned NVK/SDL3 or java-switch component as applicable'],tested_environment='Linux cross-build and host checks; NRO not executed',known_limitations=limitations)
sd=DIST/'COPY_TO_SD'
if sd.exists():shutil.rmtree(sd)
for app in verify.APPS:
    dest=sd/'switch'/app;dest.mkdir(parents=True);shutil.copyfile(DIST/(app+'.nro'),dest/(app+'.nro'))
runtime=sd/'switch/mc-runtime'
for sub in ['config','logs','runtimes/minijvm','tests','launchers','profiles','instances/java-smoke','tmp','licenses']:(runtime/sub).mkdir(parents=True,exist_ok=True)
java_manifest=json.loads((JAVA/'dist/manifest.json').read_text())
java_zip=JAVA/'dist/java-switch-test-package.zip'
java_zip_record=next(x for x in java_manifest['artifacts'] if x['name']==java_zip.name)
if hashlib.sha256(java_zip.read_bytes()).hexdigest()!=java_zip_record['sha256']:raise RuntimeError('Java test ZIP hash mismatch')
with zipfile.ZipFile(java_zip) as package:
    (runtime/'runtimes/minijvm/minijvm_rt.jar').write_bytes(package.read('switch/mc-runtime/runtimes/minijvm/minijvm_rt.jar'))
    for name in ['diagnostic-tests.jar','dependency.jar','java25-tests.jar','java25-hello.jar','java25-agent-smoke-agent.jar','java25-agent-smoke-app.jar']:
        (runtime/'tests'/name).write_bytes(package.read('switch/mc-runtime/tests/'+name))
shutil.copyfile(ROOT/'build/switchcraft-native-smoke.jar',runtime/'tests/switchcraft-native-smoke.jar')
shutil.copyfile(ROOT/'build/switchcraft-launcher-bridge.jar',runtime/'launchers/switchcraft-launcher-bridge.jar')
shutil.copyfile(ROOT/'build/switchcraft-lwjgl-horizon.jar',runtime/'launchers/switchcraft-lwjgl-horizon.jar')
image=ROOT/'build/java25-integrated/runtime/openjdk25-horizon-runtime/runtime'
shutil.copytree(image,runtime/'runtimes/openjdk25')
shutil.copyfile(ROOT/'profiles/26.4-snapshot-6.json',runtime/'profiles/26.4-snapshot-6.json')
shutil.copyfile(ROOT/'config/launcher.example.json',runtime/'config/launcher.example.json')
for base in [ROOT/'licenses',JAVA/'licenses']:
    for file in base.rglob('*'):
        if file.is_file():shutil.copyfile(file,runtime/'licenses'/file.name)
shutil.copyfile(ROOT/'LICENSE',runtime/'licenses/SWITCHCRAFT-MIT.txt')
shutil.copyfile(ROOT/'vendor/JSON-LICENSE.MIT',runtime/'licenses/NLOHMANN-JSON-MIT.txt')
shutil.copyfile(ROOT/'.deps/sdl3/share/licenses/SDL3/LICENSE.txt',runtime/'licenses/SDL3-ZLIB.txt')
for sub in ['versions','libraries','assets','mods','config','saves','resourcepacks','shaderpacks']:(sd/'minecraft/.minecraft'/sub).mkdir(parents=True,exist_ok=True)
for name in ['README.md','docs/TEST_PLAN.md','docs/KNOWN_ISSUES.md','docs/HOST_REFERENCE.md',
             'docs/DEVICE_TEST_QUICKSTART.md','docs/LAUNCHER_TESTS.md','docs/PRISM_PORT.md','docs/SD_TEST_PACKAGE.md']:
    dest=sd/'switchcraft-docs'/pathlib.Path(name).name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
shutil.copyfile(ROOT/'tools/collect-feedback.py',sd/'switchcraft-docs/collect-feedback.py')
guide=(ROOT/'docs/SD_TEST_PACKAGE.md').read_text()
for name in ['DEVICE_TEST_QUICKSTART.md','LAUNCHER_TESTS.md','TEST_PLAN.md']:
    guide=guide.replace(']('+name+')','](switchcraft-docs/'+name+')')
(sd/'START_HERE.md').write_text(guide)
(sd/'INSTALL.txt').write_text('Merge switch/ and minecraft/ onto the SD root. Preserve saves and real configuration.\nUse application-mode hbmenu. Run java25-test A, X and Y in separate fresh processes.\nHardware execution NOT TESTED. Java 25 VM is cross-linked; Minecraft does not yet run on Horizon.\nSee switchcraft-docs/TEST_PLAN.md. No game files or credentials are included.\n')
source=DIST/'switchcraft-corresponding-source.tar.gz'
curl_spec=importlib.util.spec_from_file_location('curl_source',ROOT/'scripts/prepare-curl-source.py')
curl_source=importlib.util.module_from_spec(curl_spec);curl_spec.loader.exec_module(curl_source)
curl_archive=curl_source.prepare()
with tarfile.open(source,'w:gz',dereference=True) as archive:
    for repository,prefix in [(ROOT,'switchcraft'),(JAVA,'java-switch')]:
        for name in subprocess.check_output(['git','ls-files','-z'],cwd=repository).split(b'\0'):
            if name:archive.add(repository/os.fsdecode(name),arcname=prefix+'/'+os.fsdecode(name))
    for directory in ['minijvm-source','minijvm','libffi-source']:
        archive.add(JAVA/'.deps'/directory,arcname='third-party/'+directory)
    archive.add(JAVA/'.deps/openjdk25.archive',arcname='third-party/openjdk25-upstream.tar.gz')
    archive.add(curl_archive,arcname='third-party/curl-7.69.1.tar.xz')
shutil.copyfile(source,sd/source.name)
host_result=json.loads((ROOT/'docs/evidence/snapshot6-host-result-2026-11-04.json').read_text())
manifest={'project':'Switchcraft','target':'26.4-snapshot-6','source_revision':revision,'java_switch_revision':java_revision,'source_dirty':dirty,
 'build_date':now,'toolchain':toolchain,'dependency_lock':LOCK,'hardware_verification':'NOT TESTED','java25_horizon_runtime':'CROSS-LINKED; STARTUP NOT TESTED',
 'minecraft_title_on_horizon':'NOT ACHIEVED','host_reference':host_result,'host_reference_note':'Historical host capture; its VM status describes the capture date, not the later cross-linked runtime', 'artifacts':records,'sd_resources':[],
 'known_limitations':limitations,'not_produced':{'opengl-test.nro':'Legacy branch legacy/1.12.2 only','minecraft-aot-test.nro':'No viable self-contained AOT runtime'},
 'release_tag':os.environ.get('SWITCHCRAFT_RELEASE_TAG','test-suite-2026-11-08-r2'),
 'historical_device_evidence':json.loads((ROOT/'docs/evidence/device-2026-11-08/summary.json').read_text()),
 'package_manifest_note':'Internal ZIP manifest records NRO/resources; external manifest additionally hashes the final archives.'}
for file in sorted(runtime.rglob('*.jar')):manifest['sd_resources'].append({'path':file.relative_to(sd).as_posix(),'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
manifest['runtime_image_files']=[{'path':file.relative_to(sd).as_posix(),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()} for file in sorted((runtime/'runtimes/openjdk25').rglob('*')) if file.is_file()]
(DIST/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');shutil.copyfile(DIST/'manifest.json',sd/'manifest.json')
zip_path=DIST/os.environ.get('SWITCHCRAFT_SD_ZIP','switch-minecraft-test-package.zip')
assert zip_path.parent==DIST and zip_path.suffix=='.zip', 'SD ZIP must be a basename in dist'
(sd/'switchcraft-docs/SD_FILES_SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(sd).as_posix()+'\n' for p in sorted(sd.rglob('*')) if p.is_file()))
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for p in sorted(sd.rglob('*')):
        if p.is_file():archive.write(p,p.relative_to(sd))
        elif not any(p.iterdir()):archive.writestr(p.relative_to(sd).as_posix()+'/',b'')
debug_path=DIST/'switchcraft-debug-symbols.zip'
with zipfile.ZipFile(debug_path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as debug:
    debug.writestr('build-identities.json',json.dumps({'source_revision':revision,'java_switch_revision':java_revision,
        'apps':{item['name']:item['build_id'] for item in records}},indent=2)+'\n')
    for app in verify.APPS:
        debug.write(ROOT/'build'/(app+'.elf'),app+'.elf')
        # External Java maps must come from the same pinned dependency build;
        # never reuse an old local map for a newly copied ELF.
        external={'java-test','ffi-test','zero-services-test','java25-test'}
        mapfile=(JAVA/'build'/(app+'.elf.map')) if app in external else (ROOT/'build'/(app+'.elf.map'))
        if mapfile.is_file():debug.write(mapfile,app+'.elf.map')
native_sdk=DIST/'switchcraft-native-sdk.tar.gz'
with tarfile.open(native_sdk,'w:gz') as sdk:
    sdk.add(ROOT/'include/switchcraft/native_lookup.h',arcname='include/switchcraft/native_lookup.h')
    sdk.add(ROOT/'include/switchcraft/composite_resolver.h',arcname='include/switchcraft/composite_resolver.h')
    sdk.add(ROOT/'include/switchcraft/native_symbols_jni.h',arcname='include/switchcraft/native_symbols_jni.h')
    sdk.add(ROOT/'build/libswitchcraft-native.a',arcname='lib/libswitchcraft-native.a')
    sdk.add(ROOT/'build/libswitchcraft-java-resolver.a',arcname='lib/libswitchcraft-java-resolver.a')
    sdk.add(ROOT/'docs/NATIVE_BINDINGS.md',arcname='NATIVE_BINDINGS.md')
    contract=json.dumps({'source_revision':revision,'java_switch_revision':java_revision,'target':'AArch64 Horizon libnx',
        'hardware_verification':'NOT TESTED','java_loader_integrated':False,'requires':'pinned java-switch ABI 1 SDK/JDK resolver, SDL3, NVK and libnx at final link'},indent=2).encode()+b'\n'
    entry=tarfile.TarInfo('native-contract.json');entry.size=len(contract);sdk.addfile(entry,io.BytesIO(contract))
for p,purpose in [(zip_path,'Installable native snapshot-6 bring-up package'),(source,'Project, runtime and Java class-library corresponding source'),(debug_path,'Matching AArch64 debug ELFs and available linker maps'),(native_sdk,'Experimental static native symbol lookup SDK')]:
    manifest['artifacts'].append({'name':p.name,'purpose':purpose,'source_revision':revision,'java_switch_revision':java_revision,'source_dirty':dirty,
        'build_date':now,'toolchain':toolchain,'bundled_dependencies':['Native bring-up applications, original launcher bridge/tests, source and licenses; no Minecraft game files'],
        'build_verification':'PASS','tested_environment':'Host archive/hash checks','hardware_verification':'NOT TESTED','known_limitations':limitations,
        'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(DIST/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
report=f'''# Snapshot 6 delivery report

## A. Implemented

Mainline targets 26.4-snapshot-6 and Vulkan. SDL3/VI swapchain and gamepad probe,
exact base-feature profile, NVK offscreen tests, read-only launch planning and a
hash-pinned Vulkan-only class transformation exist. Java is owned by the separate
java-switch repository and consumed at a fixed commit. A limited static SDL/Vulkan
symbol lookup is linked into the presentation probe; it is not a Java loader.
Session/stage diagnostics, an allowlisted feedback collector and matching debug
ELFs are included. Physical execution remains NOT TESTED.

## B. Artifacts

Source `{revision}`, Java source `{java_revision}`, dirty `{dirty}`.
Paths are relative to `{DIST}`.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
'''
for item in manifest['artifacts']:report+=f'| `{item["name"]}` | {item["bytes"]} | `{item["sha256"]}` |\n'
report+='''
## C. Build validation

Nine genuine NROs have matching AArch64 ELFs, NRO0/ASET/NACP/icons/build IDs.
Host tests cover metadata, fake/truncated artifact rejection, feature gates,
feedback allowlisting, native lookup and a synthetic renderer transformation.
When SWITCHCRAFT_CLIENT_JAR is supplied, its SHA-1 and renderer-class SHA-256
are verified and the actual class transformation is checked. Independent runtime
tests execute Java 8 JARs and Java 25 standard JNI/FFM/options on the host.
See build/host-tests.log and build/java-runtime.log for exact results.

## D. Hardware

All Horizon execution is NOT TESTED. Java 25 VM is cross-linked in diagnostics,
but startup and Java execution have not been verified. The Switch
Minecraft title objective is NOT ACHIEVED. The Linux Java 25 llvmpipe Vulkan Demo
reference did reach the title screen, including the strict Vulkan transformation;
its screenshot and logs are explicitly labeled HOST ONLY.

## E. Installation

Merge COPY_TO_SD or the install ZIP onto the SD root, preserve saves/configuration,
and use application-mode hbmenu. No game files or real launcher.json are included.
Import an owned installation's versions/libraries/assets if testing the inspector.

## F. First three hardware sessions

1. Native menu, memory, SD and threads in switch-diagnostics.
2. vulkan-present A for exact feature capture, then X for SDL3/VI/gamepad.
3. vulkan-test transfer/offscreen rendering, then ffi-test downcall/W^X tests.
The Java 8 suite is separate; it is not Java 25 compatibility. Export mc-runtime/logs.
The packaged collect-feedback.py creates a new archive of allowlisted logs and
the manifest. Review it and any separately attached crash reports before sharing.

## G. Architecture

See docs/ARCHITECTURE.md and docs/architecture.svg. Java source/build boundaries
and unavailable VM state are explicit; no Linux runtime is bundled for Horizon.

## H. Limits

Horizon JVM 25 execution, static LWJGL/native module loading,
shaderc/VMA/SPIR-V Cross/audio integration and device instrumentation remain open.
See docs/JAVA_INTEGRATION_HANDOFF.md and docs/NATIVE_BINDINGS.md for the exact
SDK boundary, currently linked symbols and integration requests.
Base Vulkan feature success alone does not establish game compatibility. Fabric
and arbitrary Mods are not supported. NVK remains experimental on Maxwell.

## I. Next steps

Return native SDL/VI/feature and Java25 A/X/Y/combined Hello logs; resolve actual
device failures with the independent Java task, then complete static LWJGL/FFM
and other native bindings before trying the pinned title on the console.

## J. Source and commits

The legacy baseline is preserved on branch legacy/1.12.2. main removes OpenGL and local
Java implementation ownership, pins java-switch and SDL3, and packages explicit
source/dependency/runtime/hardware evidence. Documents are English.

'''
report+='```\n'+subprocess.check_output(['git','log','--oneline','-12'],text=True)+'```\n'
(DIST/'DELIVERY_REPORT.md').write_text(report)
(DIST/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(DIST.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
print('Packaged',len(verify.APPS),'verified NROs for snapshot 6:',zip_path)
