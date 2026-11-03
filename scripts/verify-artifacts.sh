#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/verify-artifacts.py
python3 - <<'PY'
import hashlib,io,json,os,pathlib,tarfile,zipfile
root=pathlib.Path('dist')
manifest=json.loads((root/'manifest.json').read_text())
for item in manifest['artifacts']:
    p=root/item['name']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],p
for line in (root/'SHA256SUMS').read_text().splitlines():
    digest,name=line.split('  ',1)
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
with zipfile.ZipFile(root/'switch-minecraft-test-package.zip') as archive:
    assert archive.testzip() is None
    names=archive.namelist()
    assert not any('/saves/' in name and not name.endswith('/') for name in names)
    assert not any(name.startswith('minecraft/.minecraft/') and name.endswith(('.dat','.mca')) for name in names)
    for app in ['switch-diagnostics','vulkan-test','vulkan-present','java-test','ffi-test','minecraft-launcher','java25-test','zero-services-test','switchcraft-java25']:
        assert archive.read(f'switch/{app}/{app}.nro')==(root/(app+'.nro')).read_bytes()
    for resource in manifest['sd_resources']:
        assert hashlib.sha256(archive.read(resource['path'])).hexdigest()==resource['sha256']
        with zipfile.ZipFile(io.BytesIO(archive.read(resource['path']))) as jar:
            assert not any(name.lower().endswith(('.so','.dll','.dylib')) for name in jar.namelist()),resource['path']
    for resource in manifest['runtime_image_files']:
        assert hashlib.sha256(archive.read(resource['path'])).hexdigest()==resource['sha256']
    assert not any('/opengl-test/' in name for name in names)
    assert not any(name.lower().endswith(('.so','.dll','.dylib')) for name in names)
    assert 'switchcraft-docs/collect-feedback.py' in names
    assert len([name for name in names if name.endswith('.jar')])==10
with zipfile.ZipFile(root/'switchcraft-debug-symbols.zip') as debug:
    assert debug.testzip() is None
    identities=json.loads(debug.read('build-identities.json'))
    assert identities['source_revision']==manifest['source_revision']
    for item in manifest['artifacts']:
        if item['name'].endswith('.nro'):
            app=item['name'][:-4]
            assert identities['apps'][item['name']]==item['build_id']
            assert debug.read(app+'.elf')==pathlib.Path('build',app+'.elf').read_bytes()
with tarfile.open(root/'switchcraft-corresponding-source.tar.gz') as source:
    assert source.getmember('third-party/minijvm-source').isdir()
    upstream=source.extractfile('third-party/openjdk25-upstream.tar.gz')
    assert upstream is not None
    java=pathlib.Path(os.environ.get('JAVA_SWITCH_SOURCE','.deps/java-switch'))
    expected=json.loads((java/'dependencies.lock.json').read_text())['openjdk25_source']['sha256']
    assert hashlib.file_digest(upstream,'sha256').hexdigest()==expected
print('Manifest, SHA256SUMS, ZIP layout and all packaged NROs: PASS')
PY
