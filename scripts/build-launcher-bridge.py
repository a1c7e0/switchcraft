#!/usr/bin/env python3
import os,pathlib,subprocess,zipfile,shutil
root=pathlib.Path(__file__).resolve().parents[1]
java_root=pathlib.Path(os.environ.get('JAVA_SWITCH_SOURCE',str(root/'.deps/java-switch')))
jdk=next((java_root/'.deps/host-jdk25').glob('*/bin/javac'))
dest=root/'build/launcher-bridge-classes';dest.mkdir(parents=True,exist_ok=True)
shutil.rmtree(dest);dest.mkdir()
sources=sorted((root/'java/org/switchcraft/launcher').glob('*.java'))
subprocess.run([str(jdk),'--release','25','-d',str(dest),*map(str,sources)],check=True)
with zipfile.ZipFile(root/'build/switchcraft-launcher-bridge.jar','w',zipfile.ZIP_DEFLATED) as jar:
    info=zipfile.ZipInfo('META-INF/MANIFEST.MF',(2020,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
    jar.writestr(info,'Manifest-Version: 1.0\nPremain-Class: org.switchcraft.launcher.VulkanOnlyAgent\n\n')
    for p in sorted(dest.rglob('*.class')):
        info=zipfile.ZipInfo(p.relative_to(dest).as_posix(),(2020,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;jar.writestr(info,p.read_bytes())
