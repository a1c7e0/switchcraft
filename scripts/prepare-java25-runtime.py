#!/usr/bin/env python3
"""Validate and unpack the exact independently-built Java 25 SDK/image."""
import hashlib,json,os,pathlib,subprocess,tarfile,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
JAVA=pathlib.Path(os.environ.get('JAVA_SWITCH_SOURCE',ROOT/'.deps/java-switch')).resolve()
JAVA_LOCK=json.loads((ROOT/'dependencies.lock.json').read_text())['java_switch']
PIN=JAVA_LOCK['revision']

def verify_profile(data, lock=JAVA_LOCK):
    """Require the selected genuine image, rather than accepting any larger JDK."""
    profile=lock.get('build_profile','instrument')
    required={'java.base','java.instrument'}
    if profile=='minecraft':
        modules=lock.get('runtime_image_modules')
        if not isinstance(modules,list) or not modules or len(modules)!=len(set(modules)):
            raise RuntimeError('Minecraft runtime lock needs its exact module inventory')
        if not required.issubset(modules):raise RuntimeError('Minecraft runtime lock omits base/instrument')
        required=set(modules)
        if not data.get('minecraft_profile'):
            raise RuntimeError('A genuine Minecraft runtime profile is required')
    elif profile!='instrument':
        raise RuntimeError('Unknown Java runtime build profile: '+str(profile))
    if not data.get('java_instrument') or set(data.get('runtime_image_modules',[]))!=required:
        raise RuntimeError('Runtime image does not match the selected instrument-enabled profile')
    if not data.get('cross_built_genuine_vm') or data.get('link_exit_status')!=0:
        raise RuntimeError('Runtime lacks a successful genuine VM cross-link proof')
    if not {'jni-check','jvmti','serialgc','services','zero'}.issubset(data.get('jvm_features',[])):
        raise RuntimeError('Runtime VM feature set does not supply the required instrument/services support')
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def verify_archive_tree(archive_path,destination,prefix=''):
    with tarfile.open(archive_path) as source:
        expected={}
        for member in source:
            if member.isfile():
                if not member.name.startswith(prefix):raise RuntimeError('Unexpected archive member: '+member.name)
                name=member.name[len(prefix):]
                stream=source.extractfile(member)
                expected[name]=hashlib.file_digest(stream,'sha256').hexdigest()
        actual={p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()}
        if actual!=set(expected):raise RuntimeError('Unexpected extracted archive inventory')
        for name,digest in expected.items():
            if sha(destination/name)!=digest:raise RuntimeError('Extracted archive content mismatch: '+name)
def verify_unpacked(base):
    runtime=base/'runtime/openjdk25-horizon-runtime';sdk=base/'sdk'
    verify_archive_tree(JAVA/'dist/javaswitch-horizon-sdk.tar.gz',sdk)
    verify_archive_tree(JAVA/'dist/openjdk25-horizon-runtime.tar.gz',runtime,'openjdk25-horizon-runtime/')
    contract=json.loads((sdk/'runtime-contract.json').read_text())
    data=json.loads((runtime/'runtime-package.json').read_text())
    if contract['abi']!=1 or contract['built_backends']['openjdk25'] is not False:raise RuntimeError('Unexpected SDK baseline contract')
    verify_profile(data)
    if sha(sdk/'lib/libjavaswitch.a')!=data['sdk_libjavaswitch_sha256'] or sha(runtime/'native/libjvm.a')!=data['upstream_libjvm_archive_sha256']:
        raise RuntimeError('SDK or VM archive mismatch')
    if (sdk/'include/javaswitch/runtime.h').read_bytes()!=(runtime/'include/javaswitch/runtime.h').read_bytes():
        raise RuntimeError('SDK/runtime ABI header mismatch')
    for module,entry in data['native_archives'].items():
        if sha(runtime/'native'/entry['name'])!=entry['sha256']:raise RuntimeError('Provider mismatch: '+module)
    for name,digest in data['runtime_image_files'].items():
        if sha(runtime/'runtime'/name)!=digest:raise RuntimeError('Runtime image mismatch: '+name)
    for suffix,digest in data['native_resolver'].items():
        name={'c_sha256':'native_resolver.c','json_sha256':'native_resolver.json'}[suffix]
        if sha(runtime/'native'/name)!=digest:raise RuntimeError('Resolver mismatch: '+name)
    for name,digest in data['jni_headers'].items():
        if sha(runtime/'include'/name)!=digest:raise RuntimeError('JNI header mismatch: '+name)
    for name,digest in data['agent_smoke_jars'].items():
        if sha(runtime/'smoke-tests'/name)!=digest:raise RuntimeError('Agent smoke mismatch: '+name)
    actual={p.relative_to(runtime/'runtime').as_posix() for p in (runtime/'runtime').rglob('*') if p.is_file()}
    if actual!=set(data['runtime_image_files']):raise RuntimeError('Unexpected runtime image inventory')
def main():
    rev=subprocess.check_output(['git','rev-parse','HEAD'],cwd=JAVA,text=True).strip()
    if rev!=PIN or subprocess.check_output(['git','status','--porcelain'],cwd=JAVA,text=True).strip():
        raise RuntimeError('Java SDK checkout must be clean and at the exact locked revision')
    manifest=json.loads((JAVA/'dist/manifest.json').read_text())
    if manifest['source_revision']!=PIN:raise RuntimeError('Java artifact manifest revision differs from lock')
    artifacts={a['name']:a for a in manifest['artifacts']}
    files=['javaswitch-horizon-sdk.tar.gz','openjdk25-horizon-runtime.tar.gz','java-switch-source.tar.gz',
           'java-test.nro','ffi-test.nro','zero-services-test.nro','java25-test.nro','java-switch-test-package.zip']
    for name in files:
        if name not in artifacts or sha(JAVA/'dist'/name)!=artifacts[name]['sha256']:
            raise RuntimeError('Missing or mismatched Java artifact: '+name)
    target=ROOT/'build/java25-integrated';marker=target/'verified-inputs.json'
    expected={'revision':PIN,'sdk':artifacts[files[0]]['sha256'],'runtime':artifacts[files[1]]['sha256']}
    if marker.exists() and json.loads(marker.read_text())==expected:
        verify_unpacked(target)
        print('Java 25 SDK and instrument runtime input hashes verified:',PIN);return
    if target.exists():raise RuntimeError('Existing generated SDK differs; move build/java25-integrated aside before rebuilding')
    with tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='java25-prepare-') as directory:
        temp=pathlib.Path(directory)
        for name,dest in [(files[0],'sdk'),(files[1],'runtime')]:
            d=temp/dest;d.mkdir()
            with tarfile.open(JAVA/'dist'/name) as archive:archive.extractall(d,filter='data')
        verify_unpacked(temp)
        marker_tmp=temp/'verified-inputs.json';marker_tmp.write_text(json.dumps(expected,indent=2)+'\n')
        temp.rename(target)
    print('Java 25 SDK and instrument runtime input hashes verified:',PIN)
if __name__=='__main__':main()
