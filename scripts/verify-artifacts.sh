#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/verify-artifacts.py
python3 - <<'PY'
import hashlib,json,pathlib,zipfile
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
    assert not any(name.endswith(('.dat','.mca')) for name in names)
    for app in ['switch-diagnostics','vulkan-test','vulkan-present','java-test','ffi-test','minecraft-launcher']:
        assert archive.read(f'switch/{app}/{app}.nro')==(root/(app+'.nro')).read_bytes()
    for resource in manifest['sd_resources']:
        assert hashlib.sha256(archive.read(resource['path'])).hexdigest()==resource['sha256']
    assert not any('/opengl-test/' in name for name in names)
    assert len([name for name in names if name.endswith('.jar')])==5
print('Manifest, SHA256SUMS, ZIP layout and all packaged NROs: PASS')
PY
