#!/usr/bin/env python3
"""Reproduce the host-only Vulkan demo reference; never downloads into dist."""
import argparse,concurrent.futures,hashlib,json,os,pathlib,subprocess,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
VERSION='26.4-snapshot-6'
METADATA_SHA1='04be0f389fdac9f1c8b9b551c1e717104a08899d'
def fetch(url,path,sha1):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if hashlib.sha1(path.read_bytes()).hexdigest()!=sha1:raise ValueError('Existing cache file checksum mismatch: '+str(path))
    else:
        raw=urllib.request.urlopen(url,timeout=90).read()
        if hashlib.sha1(raw).hexdigest()!=sha1:raise ValueError('Download checksum mismatch')
        path.write_bytes(raw)
    return path
def allowed(lib):
    result='rules' not in lib
    for rule in lib.get('rules',[]):
        target=rule.get('os',{})
        if target.get('name','linux')=='linux' and target.get('arch','x86_64') in ['x86_64','amd64']:result=rule['action']=='allow'
    return result
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--cache',default=str(ROOT/'.cache/snapshot6-host'))
    parser.add_argument('--run-demo',action='store_true',help='Run the official demo on this Linux host, not Horizon')
    parser.add_argument('--java');parser.add_argument('--download-assets',action='store_true');a=parser.parse_args()
    cache=pathlib.Path(a.cache).resolve()
    if cache==ROOT/'dist' or ROOT/'dist' in cache.parents:raise ValueError('Game/reference cache must remain outside dist')
    path=fetch('https://piston-meta.mojang.com/v1/packages/'+METADATA_SHA1+'/'+VERSION+'.json',cache/'version.json',METADATA_SHA1)
    version=json.loads(path.read_text());client=version['downloads']['client']
    fetch(client['url'],cache/'client.jar',client['sha1'])
    libraries=[l['downloads']['artifact'] for l in version['libraries'] if allowed(l) and 'artifact' in l.get('downloads',{})]
    def library(artifact):return fetch(artifact['url'],cache/'libraries'/artifact['path'],artifact['sha1'])
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:paths=list(pool.map(library,libraries))
    classpath=os.pathsep.join(map(str,[cache/'client.jar',*paths]));(cache/'classpath.txt').write_text(classpath)
    if a.download_assets or a.run_demo:
        index=version['assetIndex'];path=fetch(index['url'],cache/'assets/indexes'/(index['id']+'.json'),index['sha1'])
        hashes={x['hash'] for x in json.loads(path.read_text())['objects'].values()}
        def asset(h):return fetch('https://resources.download.minecraft.net/'+h[:2]+'/'+h,cache/'assets/objects'/h[:2]/h,h)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(asset,hashes))
    print('Verified official snapshot 6 host cache; no game files enter Git/dist')
    if not a.run_demo:return 0
    if not os.environ.get('DISPLAY'):raise RuntimeError('An X11 display is required for this host reference')
    java=a.java or str(next((ROOT/'.deps/java-switch/.deps/host-jdk25').glob('*/bin/java')))
    command=[java,'-Xms256M','-Xmx1536M','--enable-native-access=ALL-UNNAMED','--add-exports','java.base/jdk.internal.misc=ALL-UNNAMED',
        '-javaagent:'+str(ROOT/'build/switchcraft-launcher-bridge.jar'),'-Dorg.lwjgl.util.Debug=true','-cp',classpath,'net.minecraft.client.main.Main',
        '--demo','--graphicsBackend','VULKAN','--version',VERSION,'--accessToken','','--gameDir',str(cache/'instance'),'--assetsDir',str(cache/'assets'),'--assetIndex',version['assetIndex']['id']]
    print('HOST ONLY: official demo mode; title-screen result requires visual review')
    with (cache/'host-vulkan.log').open('w') as log:return subprocess.call(command,cwd=cache,stdout=log,stderr=subprocess.STDOUT)
if __name__=='__main__':raise SystemExit(main())
