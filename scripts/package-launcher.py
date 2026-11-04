#!/usr/bin/env python3
"""Package the launcher milestone without relabelling existing runtime diagnostics."""
import gzip
import io
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import zipfile
ROOT=Path(__file__).resolve().parents[1]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip():
        raise RuntimeError('Commit the complete source before packaging the launcher')
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    info=(ROOT/'build/build-info.h').read_text()
    if '"'+revision+'"' not in info: raise RuntimeError('Rebuild the launcher from the clean final commit')
    lock=json.loads((ROOT/'dependencies.lock.json').read_text())
    dk=Path(os.environ.get('DEVKITPRO',str(ROOT/'.toolchain/opt/devkitpro')))
    curl_spec=importlib.util.spec_from_file_location('curl_source',ROOT/'scripts/prepare-curl-source.py')
    curl_source=importlib.util.module_from_spec(curl_spec);curl_spec.loader.exec_module(curl_source)
    curl_archive=curl_source.prepare()
    verified=json.loads((ROOT/'build/java25-integrated/verified-inputs.json').read_text())
    if verified['revision']!=lock['java_switch']['revision']:raise RuntimeError('Wrong cached runtime revision')
    module=importlib.util.spec_from_file_location('verify_launcher',ROOT/'scripts/verify-artifacts.py')
    verify=importlib.util.module_from_spec(module);module.loader.exec_module(verify)
    record=verify.verify(ROOT/'dist/minecraft-launcher.nro',ROOT/'build/minecraft-launcher.elf')
    dest=ROOT/'dist/launcher-foundation';dest.mkdir(exist_ok=True)
    sd=dest/'COPY_TO_SD'
    if sd.exists():shutil.rmtree(sd)
    app=sd/'switch/minecraft-launcher';app.mkdir(parents=True)
    shutil.copy2(ROOT/'dist/minecraft-launcher.nro',app/'minecraft-launcher.nro')
    shutil.copy2(ROOT/'dist/minecraft-launcher.nro',dest/'minecraft-launcher.nro')
    docs=sd/'switchcraft-docs';docs.mkdir()
    shutil.copy2(ROOT/'docs/PRISM_PORT.md',docs/'PRISM_PORT.md')
    shutil.copy2(ROOT/'docs/LAUNCHER_TESTS.md',docs/'LAUNCHER_TESTS.md')
    shutil.copy2(ROOT/'tools/collect-feedback.py',docs/'collect-feedback.py')
    for path in (ROOT/'docs/evidence/launcher').glob('*.png'):
        out=docs/'evidence/launcher'/path.name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,out)
    licenses=sd/'switch/mc-runtime/licenses';licenses.mkdir(parents=True)
    for path in (ROOT/'licenses').iterdir():
        if path.is_file():shutil.copy2(path,licenses/path.name)
    shutil.copy2(ROOT/'LICENSE',licenses/'SWITCHCRAFT-MIT.txt')
    source=dest/'launcher-corresponding-source.tar.gz'
    raw=subprocess.check_output(['git','archive','--format=tar','--prefix=switchcraft/',revision],cwd=ROOT)
    with source.open('wb') as output:
        with gzip.GzipFile(filename='',mode='wb',fileobj=output,mtime=0) as compressed:
            with tarfile.open(fileobj=compressed,mode='w|') as complete:
                with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as tracked:
                    for member in tracked:complete.addfile(member,tracked.extractfile(member) if member.isfile() else None)
                contents=curl_archive.read_bytes();member=tarfile.TarInfo('third-party/curl-7.69.1.tar.xz');member.size=len(contents);member.mode=0o644;complete.addfile(member,io.BytesIO(contents))
    shutil.copy2(source,sd/source.name)
    (sd/'INSTALL-LAUNCHER.txt').write_text('Merge switch/ and switchcraft-docs/ onto the SD root. This replaces only minecraft-launcher.nro and adds documentation/licenses/source. Preserve profiles, saves, existing configuration and logs.\nUse application-mode hbmenu. L/R: section; D-pad/stick: focus; A: select; B: back; X: new instance; +: close. Y in Versions refreshes the catalog. Use Install / repair, Create, Verify, Import and Archive/Restore from the UI. Active jobs cancel and join before exit. Touch and networking are implemented but hardware untested.\nThe new NRO is VM-free. Minecraft cannot launch on Horizon. The UI uses system shared fonts; the console inspector is the fallback if unavailable.\nInstall the full published Java25 test package separately for diagnostic NROs and runtime images. SDK corresponding source is supplied by the base artifact set artifacts/java25-e08f36a (runtime b7c2ac7). The current launcher and port source is included here.\nAll physical Horizon execution is NOT TESTED. See switchcraft-docs/LAUNCHER_TESTS.md and PRISM_PORT.md.\n')
    overlay=dest/'switchcraft-launcher-foundation.zip'
    with zipfile.ZipFile(overlay,'w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(sd.rglob('*')):
            if path.is_file():z.write(path,path.relative_to(sd))
    debug=dest/'launcher-debug-symbols.zip'
    with zipfile.ZipFile(debug,'w',zipfile.ZIP_DEFLATED) as z:
        for name in ['minecraft-launcher.elf','minecraft-launcher.elf.map']:z.write(ROOT/'build'/name,name)
    manifest={'source_revision':revision,'java_switch_revision':lock['java_switch']['revision'],
        'prism_revision':'059e858e101edc9314ccb94aa48bd01b282539c5','sdk_abi':1,
        'sdk_library_sha256':digest(ROOT/'build/java25-integrated/sdk/lib/libjavaswitch.a'),
        'cached_runtime_input':verified,'launcher':record,'horizon_execution':'NOT TESTED',
        'vm_linked':False,'minecraft_launch_enabled':False,'online_installation_implemented':True,
        'network_tls':'libcurl/libnx SSL, certificate verification enabled; device NOT TESTED',
        'native_curl_library_sha256':digest(dk/'portlibs/switch/lib/libcurl.a'),
        'curl_source_provenance':json.loads((ROOT/'vendor/curl/UPSTREAM.json').read_text()),
        'host_installation_evidence':json.loads((ROOT/'docs/evidence/launcher-online-install-HOST-ONLY.json').read_text()),'host_ui_preview':'rendered from original display fixtures',
        'unchanged_runtime_source':'https://github.com/a1c7e0/switchcraft/tree/artifacts/java25-e08f36a',
        'artifacts':[{ 'name':p.name,'sha256':digest(p),'bytes':p.stat().st_size} for p in [dest/'minecraft-launcher.nro',overlay,source,debug]]}
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (dest/'SHA256SUMS').write_text(''.join(digest(p)+'  '+p.name+'\n' for p in [dest/'minecraft-launcher.nro',overlay,source,debug,dest/'manifest.json']))
    print(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
