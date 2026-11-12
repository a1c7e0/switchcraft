#!/usr/bin/env python3
"""Compile LWJGL 3.4.3 Horizon platform/loader overrides against pinned APIs."""
import hashlib,json,os,pathlib,subprocess,tempfile,urllib.request,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
LOCK=json.loads((ROOT/'dependencies.lock.json').read_text())
def fetch(name):
    entry=LOCK[name];path=ROOT/'.deps'/(name+'.jar');path.parent.mkdir(exist_ok=True)
    if not path.exists():
        partial=path.with_suffix('.partial')
        urllib.request.urlretrieve(entry['url'],partial)
        if hashlib.sha256(partial.read_bytes()).hexdigest()!=entry['sha256']:
            raise ValueError(name+' checksum mismatch')
        partial.replace(path)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
        raise ValueError(name+' checksum mismatch')
    return path

def main():
    deps=[fetch('lwjgl_core'),fetch('jspecify'),fetch('lwjgl_vulkan'),fetch('lwjgl_openal'),fetch('lwjgl_opengl')]
    jdk=next((ROOT/'.deps/host-jdk25').glob('*/bin/javac'))
    with tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='lwjgl-horizon-') as directory:
        work=pathlib.Path(directory)
        sources=sorted((ROOT/'vendor/lwjgl-horizon/org/lwjgl/system').glob('*.java'))
        sources += [ROOT/'vendor/lwjgl-horizon/org/lwjgl/vulkan/VK.java',
                    ROOT/'vendor/lwjgl-horizon/org/lwjgl/openal/ALC.java',
                    ROOT/'vendor/lwjgl-horizon/org/lwjgl/opengl/GL.java']
        sources.append(ROOT/'java/org/switchcraft/runtime/NativeSymbols.java')
        subprocess.run([str(jdk),'--release','25','-cp',os.pathsep.join(map(str,deps)),'-d',str(work),*map(str,sources)],check=True)
        allowed={'Platform','Library','HorizonSharedLibrary','Configuration','NativeSymbols','VK','ALC','GL'}
        files=[p for p in sorted(work.rglob('*.class')) if p.stem.split('$')[0] in allowed]
        required={'Platform.class','Library.class','HorizonSharedLibrary.class','Configuration.class',
                  'NativeSymbols.class','VK.class','ALC.class','GL.class'}
        if not required.issubset({p.name for p in files}):raise RuntimeError('LWJGL Horizon compatibility classes missing')
        with zipfile.ZipFile(ROOT/'build/switchcraft-lwjgl-horizon.jar','w',zipfile.ZIP_DEFLATED) as jar:
            for p in files:
                info=zipfile.ZipInfo(p.relative_to(work).as_posix(),(2020,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;jar.writestr(info,p.read_bytes())
            info=zipfile.ZipInfo('META-INF/LWJGL-LICENSE.txt',(2020,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;jar.writestr(info,(ROOT/'licenses/LWJGL-BSD-3-Clause.txt').read_bytes())
    print('Built LWJGL Horizon core/Vulkan/OpenAL/GL overrides and NativeSymbols bridge; native binding completeness NOT CLAIMED')
if __name__=='__main__':main()
