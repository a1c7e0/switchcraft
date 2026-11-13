#!/usr/bin/env python3
"""Package the pinned snapshot-6 native bring-up without shipping game files."""
import datetime,hashlib,importlib.util,io,json,os,pathlib,shutil,subprocess,tarfile,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1];os.chdir(ROOT);DIST=ROOT/'dist'
legacy_payload_zip=DIST/'switchcraft-build-payload-2026-11-12-r4.zip'
if legacy_payload_zip.exists():legacy_payload_zip.unlink()
slim_output=DIST/'device-test-slim'
if slim_output.exists():shutil.rmtree(slim_output)
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
    'R3 zero-services launch was reported unsuccessful without a supplied log; cause unresolved; R4 stack hardening and main-entry marker are not a demonstrated startup fix',
    'Host-only strict Vulkan demo title verified; this is not a Horizon result','NVK Maxwell is experimental/nonconformant',
 'SDL3/VI presentation and libffi W^X closures compiled, awaiting physical tests','LWJGL core JNI, VMA, FreeType/OpenAL loopback, STB, shaderc, and SPIR-V Cross bindings are cross-built, not device-tested; these are focused diagnostics rather than complete game-library coverage',
    'Fabric, account authentication and arbitrary Mods not implemented']
purposes={'switch-diagnostics.nro':'Native memory, SD, input, threads and next-load menu',
 'vulkan-test.nro':'NVK transfer/readback and offscreen triangle',
 'vulkan-present.nro':'Exact snapshot-6 base features, SDL3 gamepad/window and VI swapchain presentation',
 'minecraft-launcher.nro':'Read-only instance planning, strict Vulkan arguments and explicit Java-25 runtime gate',
 'java-test.nro':'Independent java-switch Java-8 interpreter diagnostic; not a Java-25 VM',
 'ffi-test.nro':'AAPCS64 downcalls, libnx W^X upcalls and whole-region memory probe',
 'zero-services-test.nro':'Standalone OpenJDK native service diagnostic, without a VM',
 'java25-test.nro':'Independent genuine Java 25 VM A/X/Y diagnostic; Horizon startup untested',
 'switchcraft-java25.nro':'Genuine Java 25 Hello and JNI/FFM SDL/LWJGL/Vulkan diagnostics with composed provider; Horizon startup untested'}
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
for sub in ['config','logs','runtimes/minijvm','tests','launchers','libraries','profiles','instances/java-smoke','tmp','licenses']:(runtime/sub).mkdir(parents=True,exist_ok=True)
java_manifest=json.loads((JAVA/'dist/manifest.json').read_text())
java_zip=JAVA/'dist/java-switch-test-package.zip'
java_zip_record=next(x for x in java_manifest['artifacts'] if x['name']==java_zip.name)
if hashlib.sha256(java_zip.read_bytes()).hexdigest()!=java_zip_record['sha256']:raise RuntimeError('Java test ZIP hash mismatch')
with zipfile.ZipFile(java_zip) as package:
    (runtime/'runtimes/minijvm/minijvm_rt.jar').write_bytes(package.read('switch/mc-runtime/runtimes/minijvm/minijvm_rt.jar'))
    for name in ['diagnostic-tests.jar','dependency.jar','java25-tests.jar','java25-hello.jar','java25-agent-smoke-agent.jar','java25-agent-smoke-app.jar']:
        (runtime/'tests'/name).write_bytes(package.read('switch/mc-runtime/tests/'+name))
shutil.copyfile(ROOT/'build/switchcraft-native-smoke.jar',runtime/'tests/switchcraft-native-smoke.jar')
# Install the classpath JARs in the pinned Vulkan Horizon profile. OpenGL is
# deliberately excluded from the Switch runtime profile.
library_profile = ['jspecify','lwjgl_core','lwjgl_sdl','lwjgl_vulkan','lwjgl_freetype',
                   'lwjgl_openal','lwjgl_stb','lwjgl_vma','lwjgl_shaderc','lwjgl_spvc']
library_inventory = []
for name in library_profile:
    entry = LOCK[name]
    jar = ROOT/'.deps'/(name+'.jar')
    if not jar.is_file() or hashlib.sha256(jar.read_bytes()).hexdigest()!=entry['sha256']:
        raise RuntimeError(f'Pinned classpath JAR missing or hash mismatch: {name}')
    filename=pathlib.PurePosixPath(entry['url'].split('?',1)[0]).name
    destination=runtime/'libraries'/filename
    shutil.copyfile(jar,destination)
    library_inventory.append({'lock_key':name,'path':destination.relative_to(sd).as_posix(),
                              'sha256':entry['sha256'],'version':entry.get('version')})
shutil.copyfile(ROOT/'build/switchcraft-launcher-bridge.jar',runtime/'launchers/switchcraft-launcher-bridge.jar')
shutil.copyfile(ROOT/'build/switchcraft-lwjgl-horizon.jar',runtime/'launchers/switchcraft-lwjgl-horizon.jar')
image=ROOT/'build/java25-integrated/runtime/openjdk25-horizon-runtime/runtime'
image_package=image.parent/'runtime-package.json'
image_profile=json.loads(image_package.read_text())
profile_files=image_profile.get('runtime_image_files',{})
if not isinstance(profile_files,dict) or not profile_files:
    raise RuntimeError('Java runtime package has no profile-driven image inventory')
required_profile_modules=LOCK.get('java_switch',{}).get('runtime_image_modules',[])
if (not isinstance(required_profile_modules,list) or len(required_profile_modules)!=10 or
        len(set(required_profile_modules))!=10 or not {'java.base','java.instrument'}<=set(required_profile_modules)):
    raise RuntimeError('dependencies.lock.json must pin the ten-module Java 25 Minecraft profile')
profile_modules=image_profile.get('modules',image_profile.get('runtime_image_modules',[]))
if not isinstance(profile_modules,list) or set(profile_modules)!=set(required_profile_modules):
    raise RuntimeError('Java runtime package module inventory differs from the pinned Minecraft profile')
if image_profile.get('minecraft_profile') is not True:
    raise RuntimeError('Java runtime package is not marked as the full Minecraft profile')
if image_profile.get('java_instrument') is not True or 'java.instrument' not in profile_modules:
    raise RuntimeError('Java runtime package lacks the required Java instrumentation module')
image_files={p.relative_to(image).as_posix():p for p in image.rglob('*') if p.is_file()}
if set(image_files)!=set(profile_files):
    raise RuntimeError('Java runtime image files differ from the pinned package profile')
runtime_image=runtime/'runtimes/openjdk25'
for relative,expected in sorted(profile_files.items()):
    source_file=image_files[relative]
    actual=hashlib.sha256(source_file.read_bytes()).hexdigest()
    if actual!=expected:
        raise RuntimeError('Java runtime profile file hash mismatch: '+relative)
    destination=runtime_image/relative
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source_file,destination)
shutil.copyfile(ROOT/'profiles/26.4-snapshot-6.json',runtime/'profiles/26.4-snapshot-6.json')
shutil.copyfile(ROOT/'config/launcher.example.json',runtime/'config/launcher.example.json')
for base,prefix in [(ROOT/'licenses','switchcraft'),(JAVA/'licenses','java-switch')]:
    for file in base.rglob('*'):
        if file.is_file():
            destination=runtime/'licenses'/prefix/file.relative_to(base)
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(file,destination)
shutil.copyfile(ROOT/'LICENSE',runtime/'licenses/SWITCHCRAFT-MIT.txt')
shutil.copyfile(ROOT/'vendor/JSON-LICENSE.MIT',runtime/'licenses/NLOHMANN-JSON-MIT.txt')
shutil.copyfile(ROOT/'.deps/sdl3/share/licenses/SDL3/LICENSE.txt',runtime/'licenses/SDL3-ZLIB.txt')
source=DIST/'switchcraft-source-2026-11-12-r4.tar.gz'
curl_spec=importlib.util.spec_from_file_location('curl_source',ROOT/'scripts/prepare-curl-source.py')
curl_source=importlib.util.module_from_spec(curl_spec);curl_spec.loader.exec_module(curl_source)
curl_archive=curl_source.prepare()
source_components=[]
source_license_files=[]
def add_pinned_source(archive,name,path,expected,arcname):
    path=pathlib.Path(path)
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
        raise RuntimeError('Pinned source archive missing or hash mismatch: '+name)
    archive.add(path,arcname=arcname)
    source_components.append({'name':name,'path':arcname,'sha256':expected})
with tarfile.open(source,'w:gz',dereference=True) as archive:
    for repository,prefix in [(ROOT,'switchcraft'),(JAVA,'java-switch')]:
        for name in subprocess.check_output(['git','ls-files','-z'],cwd=repository).split(b'\0'):
            if name:archive.add(repository/os.fsdecode(name),arcname=prefix+'/'+os.fsdecode(name))
    for directory in ['minijvm-source','minijvm','libffi-source']:
        archive.add(JAVA/'.deps'/directory,arcname='third-party/'+directory)
    java_lock=json.loads((JAVA/'dependencies.lock.json').read_text())
    add_pinned_source(archive,'OpenJDK 25 upstream',JAVA/'.deps/openjdk25.archive',
        java_lock['openjdk25_source']['sha256'],'third-party/openjdk25-upstream.tar.gz')
    add_pinned_source(archive,'LWJGL 3.4.3',ROOT/'.deps/lwjgl_core_source.archive',
        LOCK['lwjgl_core']['source_archive_sha256'],'third-party/upstream/lwjgl3-upstream.tar.gz')
    openal=LOCK['openal_soft']
    add_pinned_source(archive,'OpenAL Soft '+openal['version'],ROOT/'.deps/openal-soft-'+openal['version']+'.tar.gz',
        openal['source_archive_sha256'],'third-party/upstream/openal-soft-'+openal['version']+'.tar.gz')
    for name,pin in sorted(LOCK['shader_libraries'].items()):
        add_pinned_source(archive,'Shader library '+name,
            ROOT/'.deps/shader-libraries'/(name+'-'+pin['source_revision']+'.tar.gz'),
            pin['source_archive_sha256'],'third-party/upstream/'+name+'-'+pin['source_revision']+'.tar.gz')
    ffi_pin=java_lock['libffi']
    add_pinned_source(archive,'libffi '+ffi_pin['tag'],JAVA/'.deps/libffi.archive',ffi_pin['sha256'],
        'third-party/upstream/libffi-'+ffi_pin['tag']+'.tar.gz')
    curl_pin=json.loads((ROOT/'vendor/curl/UPSTREAM.json').read_text())
    add_pinned_source(archive,'curl 7.69.1',curl_archive,curl_pin['source_sha256'],
        'third-party/curl-7.69.1.tar.xz')
    for base,prefix in [(ROOT/'licenses','switchcraft'),(JAVA/'licenses','java-switch')]:
        if base.is_dir():
            for file in sorted(base.rglob('*')):
                if file.is_file():
                    arcname='third-party/licenses/'+prefix+'/'+file.relative_to(base).as_posix()
                    archive.add(file,arcname=arcname)
                    source_license_files.append({'path':arcname,'bytes':file.stat().st_size,
                                                 'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
host_result=json.loads((ROOT/'docs/evidence/snapshot6-host-result-2026-11-04.json').read_text())
manifest={'project':'Switchcraft','target':'26.4-snapshot-6','source_revision':revision,'java_switch_revision':java_revision,'source_dirty':dirty,
 'build_date':now,'toolchain':toolchain,'dependency_lock':LOCK,'hardware_verification':'NOT TESTED','java25_horizon_runtime':'CROSS-LINKED; STARTUP NOT TESTED',
 'minecraft_title_on_horizon':'NOT ACHIEVED','host_reference':host_result,'host_reference_note':'Historical host capture; its VM status describes the capture date, not the later cross-linked runtime', 'artifacts':records,'sd_resources':[],
 'known_limitations':limitations,'not_produced':{'opengl-test.nro':'Legacy branch legacy/1.12.2 only','minecraft-aot-test.nro':'No viable self-contained AOT runtime'},
 'release_tag':os.environ.get('SWITCHCRAFT_RELEASE_TAG','test-suite-2026-11-12-r4'),
 'runtime_image_modules':profile_modules,'runtime_minecraft_profile':True,
 'source_companions':source_components,
 'source_licenses':source_license_files,
 'source_license_trees':['third-party/licenses/switchcraft/','third-party/licenses/java-switch/'],
 'historical_device_evidence':json.loads((ROOT/'docs/evidence/device-2026-11-08/summary.json').read_text()),
 'package_manifest_note':'The minimal SD package has its own final manifest and in-ZIP hashes; this build manifest hashes the separate source, debug and native SDK companions.'}
for file in sorted(p for p in runtime.rglob('*') if p.is_file() and
                   not p.relative_to(runtime).as_posix().startswith('runtimes/openjdk25/')):
    manifest['sd_resources'].append({'path':file.relative_to(sd).as_posix(),'bytes':file.stat().st_size,
                                     'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
manifest['runtime_and_test_jars']=[{'path':item['path'],'bytes':item['bytes'],'sha256':item['sha256']}
    for item in manifest['sd_resources'] if item['path'].startswith('switch/mc-runtime/') and item['path'].endswith('.jar')]
manifest['runtime_image_files']=[{'path':file.relative_to(sd).as_posix(),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()} for file in sorted((runtime/'runtimes/openjdk25').rglob('*')) if file.is_file()]
(DIST/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
debug_path=DIST/'switchcraft-debug-symbols.zip'
with zipfile.ZipFile(debug_path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as debug:
    debug.writestr('build-identities.json',json.dumps({'source_revision':revision,'java_switch_revision':java_revision,
        'apps':{item['name']:item['build_id'] for item in records}},indent=2)+'\n')
    for app in verify.APPS:
        debug.write(ROOT/'build'/(app+'.elf'),app+'.elf')
        # External Java maps must come from the same pinned dependency build;
        # never reuse an old local map for a newly copied ELF.
        external={'java-test','ffi-test','zero-services-test','java25-test'}
        # The SDK importer selects the profile-specific ELF and matching map.
        mapfile=ROOT/'build'/(app+'.elf.map')
        if mapfile.is_file():debug.write(mapfile,app+'.elf.map')
native_sdk=DIST/'switchcraft-native-sdk.tar.gz'
with tarfile.open(native_sdk,'w:gz') as sdk:
    for header in ['native_lookup.h','composite_resolver.h','native_symbols_jni.h','lwjgl_core.h',
                   'lwjgl_utilities.h','font_audio.h','shader_libraries.h']:
        sdk.add(ROOT/'include/switchcraft'/header,arcname='include/switchcraft/'+header)
    sdk_libraries=[
        ('build/libswitchcraft-native.a','lib/libswitchcraft-native.a'),
        ('build/libswitchcraft-java-resolver.a','lib/libswitchcraft-java-resolver.a'),
        ('build/lwjgl-core/horizon/liblwjgl-core.a','lib/liblwjgl-core.a'),
        ('build/lwjgl-utilities/horizon/liblwjgl-utilities.a','lib/liblwjgl-utilities.a'),
        ('build/font-audio/horizon/libswitchcraft-font-audio.a','lib/libswitchcraft-font-audio.a'),
        ('build/font-audio/openal-cross/libopenal.a','lib/libopenal.a'),
        ('build/shader-libraries/horizon/libswitchcraft-shader-libraries-provider.a','lib/libswitchcraft-shader-libraries-provider.a'),
        ('build/shader-libraries/horizon/shaderc/libshaderc/libshaderc_combined.a','lib/libshaderc_combined.a'),
        ('.deps/sdl3/lib/libSDL3.a','lib/libSDL3.a'),
        ('.deps/nvk/lib/libvulkan.a','lib/libvulkan.a'),
        ('build/java25-integrated/sdk/lib/libjavaswitch.a','lib/libjavaswitch.a'),
        ('build/jdk_native_resolver.o','lib/jdk_native_resolver.o'),
    ]
    sdk_libraries.extend((f'build/shader-libraries/horizon/spirv-cross/libspirv-cross-{module}.a',
                         f'lib/libspirv-cross-{module}.a')
                         for module in ['c','core','glsl','hlsl','msl','cpp','reflect'])
    sdk_libraries.extend((str(path.relative_to(ROOT)), 'lib/openjdk-native/'+path.name)
                         for path in sorted((ROOT/'build/java25-integrated/runtime/openjdk25-horizon-runtime/native').glob('*.a')))
    for path,arcname in sdk_libraries:sdk.add(ROOT/path,arcname=arcname)
    sdk.add(ROOT/'dependencies.lock.json',arcname='dependencies.lock.json')
    for source_root,arcname in [
        (ROOT/'build/java25-integrated/sdk/include','java-sdk/include'),
        (ROOT/'build/java25-integrated/runtime/openjdk25-horizon-runtime/include','openjdk25/include'),
    ]:
        if not source_root.is_dir():raise RuntimeError('Static SDK header tree is missing: '+str(source_root))
        sdk.add(source_root,arcname=arcname)
    for name in ['native_resolver.c','native_resolver.json']:
        sdk.add(ROOT/'build/java25-integrated/runtime/openjdk25-horizon-runtime/native'/name,
                arcname='openjdk25/native/'+name)
    sdk.add(ROOT/'docs/NATIVE_BINDINGS.md',arcname='NATIVE_BINDINGS.md')
    contract=json.dumps({'source_revision':revision,'java_switch_revision':java_revision,'target':'AArch64 Horizon libnx',
        'hardware_verification':'NOT TESTED','lwjgl_native_adapters_cross_built':True,
        'combined_diagnostic_nro_links_adapters':True,
        'adapter_execution':'NOT TESTED','minecraft_title_integrated':False,
        'included_link_artifacts':[arcname for _,arcname in sdk_libraries],
        'jdk_native_resolver':{'object':'lib/jdk_native_resolver.o','source':'openjdk25/native/native_resolver.c',
            'data':'openjdk25/native/native_resolver.json','header':'openjdk25/include/javaswitch/native_resolver.h',
            'link_with':'lib/libswitchcraft-java-resolver.a and pinned OpenJDK native archives'},
        'link_order_note':'Keep provider objects and archives before their definitions; group circularly dependent OpenJDK, SDL3, NVK, OpenAL and shader archives as in the pinned Makefile link recipe.',
        'requires':'pinned java-switch ABI 1 SDK/JDK resolver, these provider archives, devkitPro libnx and portlibs (FreeType, HarfBuzz, PNG, BZip2, curl, Nouveau, zstd, z, math and pthread) at final link'},indent=2).encode()+b'\n'
    entry=tarfile.TarInfo('native-contract.json');entry.size=len(contract);sdk.addfile(entry,io.BytesIO(contract))
for p,purpose in [(source,'Project and corresponding source plus pinned upstream archives and license texts'),
                   (debug_path,'Matching AArch64 debug ELFs and available linker maps'),
                   (native_sdk,'Experimental AArch64 static relink SDK; requires the listed external devkitPro portlibs')]:
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

R4 Horizon execution is NOT TESTED. Historical R3 feedback established that
JNI_CreateJavaVM returned and vm-ready was reached, then Hello/JNI/agent
class-loading attempts failed because classes were missing. That evidence is
preserved and does not establish successful Java workload execution. The
Switch Minecraft title objective is NOT ACHIEVED. The Linux Java 25 llvmpipe
Vulkan Demo reference did reach the title screen, including the strict Vulkan
transformation; its screenshot and logs are explicitly labeled HOST ONLY.

## E. Installation

Use the separate minimal device-test ZIP from `device-test-slim/` after its
manifest and hashes have been reviewed. The full build payload is intermediate,
not the SD distribution. Extract the minimal ZIP onto the SD root, preserve
saves/configuration, and use application-mode hbmenu. No game files or real
launcher.json are included.

## F. First three hardware sessions

1. One fresh `java25-test` A attempt. Continue to X/Y only when each prerequisite
   passes; use a new application process for every VM action.
2. After successful standalone A/X/Y, make combined A, X, then Y attempts,
   again with a fresh process for every action.
3. Run optional native and Vulkan checks separately. These do not establish
   Java 25 execution or Minecraft launch. The Java 8 suite is separate.
Export mc-runtime/logs.
The packaged collect-feedback.py creates a new archive of allowlisted logs and
the manifest. Review it and any separately attached crash reports before sharing.

## G. Architecture

See docs/ARCHITECTURE.md and docs/architecture.svg. Java source/build boundaries
and unavailable VM state are explicit; no Linux runtime is bundled for Horizon.

## H. Limits

Horizon JVM 25 execution and device instrumentation remain open. The focused
LWJGL, VMA, FreeType/OpenAL, STB, shaderc and SPIR-V Cross providers are
cross-built but unverified on hardware; complete game-library coverage remains open.
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
print('Prepared minimal SD tree and companion artifacts for snapshot 6')
subprocess.run(['python3',str(ROOT/'scripts/package-device-slim.py')],check=True)
