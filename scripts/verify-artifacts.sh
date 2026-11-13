#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/verify-artifacts.py
python3 - <<'PY'
import hashlib,io,json,os,pathlib,tarfile,zipfile
root=pathlib.Path('dist')
manifest=json.loads((root/'manifest.json').read_text())
lock=json.loads(pathlib.Path('dependencies.lock.json').read_text())
assert {item['name'] for item in manifest['artifacts'] if item['name'].endswith('.zip')} == {'switchcraft-debug-symbols.zip'}, 'only the separate debug ZIP belongs in the build manifest'
for item in manifest['artifacts']:
    p=root/item['name']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],p
for line in (root/'SHA256SUMS').read_text().splitlines():
    digest,name=line.split('  ',1)
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
expected_modules=set(lock['java_switch']['runtime_image_modules'])
assert len(expected_modules)==10 and {'java.base','java.instrument'}<=expected_modules
with zipfile.ZipFile(root/'switchcraft-debug-symbols.zip') as debug:
    assert debug.testzip() is None
    identities=json.loads(debug.read('build-identities.json'))
    assert identities['source_revision']==manifest['source_revision']
    for item in manifest['artifacts']:
        if item['name'].endswith('.nro'):
            app=item['name'][:-4]
            assert identities['apps'][item['name']]==item['build_id']
            assert debug.read(app+'.elf')==pathlib.Path('build',app+'.elf').read_bytes()
with tarfile.open(root/'switchcraft-source-2026-11-13-r5.tar.gz') as source:
    assert source.getmember('third-party/minijvm-source').isdir()
    upstream=source.extractfile('third-party/openjdk25-upstream.tar.gz')
    assert upstream is not None
    java=pathlib.Path(os.environ.get('JAVA_SWITCH_SOURCE','.deps/java-switch'))
    java_lock=json.loads((java/'dependencies.lock.json').read_text())
    expected=java_lock['openjdk25_source']['sha256']
    assert hashlib.file_digest(upstream,'sha256').hexdigest()==expected
    lwjgl=source.extractfile('third-party/upstream/lwjgl3-upstream.tar.gz')
    assert lwjgl is not None
    lwjgl_expected=lock['lwjgl_core']['source_archive_sha256']
    assert hashlib.file_digest(lwjgl,'sha256').hexdigest()==lwjgl_expected
    expected_sources={
        'third-party/openjdk25-upstream.tar.gz':java_lock['openjdk25_source']['sha256'],
        'third-party/upstream/lwjgl3-upstream.tar.gz':lock['lwjgl_core']['source_archive_sha256'],
        'third-party/upstream/openal-soft-'+lock['openal_soft']['version']+'.tar.gz':lock['openal_soft']['source_archive_sha256'],
        'third-party/upstream/libffi-'+java_lock['libffi']['tag']+'.tar.gz':java_lock['libffi']['sha256'],
        'third-party/curl-7.69.1.tar.xz':json.loads(pathlib.Path('vendor/curl/UPSTREAM.json').read_text())['source_sha256'],
    }
    for name,pin in lock['shader_libraries'].items():
        expected_sources['third-party/upstream/'+name+'-'+pin['source_revision']+'.tar.gz']=pin['source_archive_sha256']
    source_components=manifest['source_companions']
    assert {item['path'] for item in source_components}==set(expected_sources)
    for item in source_components:
        assert item['sha256']==expected_sources[item['path']]
        member=source.extractfile(item['path'])
        assert member is not None
        assert hashlib.file_digest(member,'sha256').hexdigest()==item['sha256'],item['path']
    license_records=manifest['source_licenses']
    license_paths={item['path'] for item in license_records}
    required_prefixes=('third-party/licenses/switchcraft/','third-party/licenses/java-switch/')
    assert all(any(path.startswith(prefix) for prefix in required_prefixes) for path in license_paths)
    assert all(any(path.startswith(prefix) for path in license_paths) for prefix in required_prefixes)
    source_license_paths={name for name in source.getnames()
                           if any(name.startswith(prefix) for prefix in required_prefixes)}
    assert source_license_paths==license_paths
    for item in license_records:
        member=source.extractfile(item['path'])
        assert member is not None
        data=member.read()
        assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'],item['path']
slim_root=root/'device-test-slim'
slim_manifest=json.loads((slim_root/'manifest.json').read_text())
slim_zip=slim_root/'switchcraft-test-suite-2026-11-13-r5.zip'
assert hashlib.sha256(slim_zip.read_bytes()).hexdigest()==slim_manifest['archive']['sha256']
assert slim_manifest['archive']['name']==slim_zip.name
with zipfile.ZipFile(slim_zip) as slim:
    assert slim.testzip() is None
    slim_names=set(slim.namelist())
    installed={item['path']:item for item in slim_manifest['sd_files']}
    assert slim_names==set(installed)|{'manifest.json','switch/mc-runtime/SD_FILES_SHA256SUMS'}
    assert all(name.startswith('switch/') or name in {'README.md','START_HERE.md','manifest.json'} for name in slim_names)
    assert len([name for name in slim_names if name.endswith('.nro')])==9
    assert {name for name in slim_names if name.startswith('switch/mc-runtime/') and name.endswith('.jar')}=={
        item['path'] for item in slim_manifest['runtime_and_test_jars']}
    assert len(slim_manifest['runtime_and_test_jars'])==20
    assert not any(name.startswith(('switchcraft-docs/','minecraft/')) for name in slim_names)
    assert not any(name.endswith(('.elf','.o','.a','.debug','.tar.gz')) for name in slim_names)
    source_record=slim_manifest['source_archive']
    source_path=root/source_record['name']
    assert source_record['name']=='switchcraft-source-2026-11-13-r5.tar.gz'
    assert source_path.stat().st_size==source_record['bytes']
    assert hashlib.sha256(source_path.read_bytes()).hexdigest()==source_record['sha256']
    assert source_record['lwjgl_upstream_sha256']==lock['lwjgl_core']['source_archive_sha256']
    with tarfile.open(source_path) as source:
        for component in source_record['components']:
            member=source.extractfile(component['path'])
            assert member is not None
            assert hashlib.file_digest(member,'sha256').hexdigest()==component['sha256'],component['path']
        assert source_record['licenses']==license_records
    assert slim_manifest['runtime_minecraft_profile'] is True
    assert set(slim_manifest['runtime_image_modules'])==expected_modules
    assert slim_manifest['hardware_verification']=='NOT TESTED'
    assert slim_manifest['zero_services_launch_observation'].startswith('R4 zero-services-test opened')
    for name,record in installed.items():
        payload=slim.read(name)
        assert len(payload)==record['bytes'] and hashlib.sha256(payload).hexdigest()==record['sha256'],name
    sums={line.split('  ',1)[1]:line.split('  ',1)[0]
          for line in slim.read('switch/mc-runtime/SD_FILES_SHA256SUMS').decode().splitlines()}
    assert sums=={name:hashlib.sha256(slim.read(name)).hexdigest() for name in installed}|{
        'manifest.json':hashlib.sha256(slim.read('manifest.json')).hexdigest()}
    assert 'switch/mc-runtime/libraries/lwjgl-3.4.3.jar' in slim_names
with tarfile.open(root/'switchcraft-native-sdk.tar.gz') as sdk:
    sdk_names=set(sdk.getnames())
    required_sdk={
        'lib/libSDL3.a','lib/libvulkan.a','lib/libopenal.a','lib/libjavaswitch.a',
        'lib/liblwjgl-core.a','lib/liblwjgl-utilities.a','lib/libswitchcraft-font-audio.a',
        'lib/libswitchcraft-shader-libraries-provider.a','lib/libshaderc_combined.a',
        'lib/libspirv-cross-c.a','lib/libspirv-cross-core.a','lib/libspirv-cross-glsl.a',
        'lib/libspirv-cross-hlsl.a','lib/libspirv-cross-msl.a','lib/libspirv-cross-cpp.a',
        'lib/libspirv-cross-reflect.a','include/switchcraft/font_audio.h',
        'include/switchcraft/shader_libraries.h','lib/jdk_native_resolver.o',
        'openjdk25/native/native_resolver.c','openjdk25/native/native_resolver.json',
        'openjdk25/include/javaswitch/native_resolver.h','native-contract.json',
    }
    assert required_sdk <= sdk_names
print('Manifest, SHA256SUMS, ZIP layout and all packaged NROs: PASS')
PY
