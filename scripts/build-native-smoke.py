#!/usr/bin/env python3
"""Build the original Java 25 JNI/FFM resolver smoke workload."""
import importlib.util,os,pathlib,subprocess,tempfile,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
javac=next((ROOT/'.deps/host-jdk25').glob('*/bin/javac'))
spec=importlib.util.spec_from_file_location('lwjgl_dependencies',ROOT/'scripts/build-lwjgl-horizon.py')
deps=importlib.util.module_from_spec(spec);spec.loader.exec_module(deps)
classpath=os.pathsep.join(str(deps.fetch(name)) for name in [
    'lwjgl_core','lwjgl_sdl','lwjgl_vulkan','lwjgl_freetype','lwjgl_openal',
    'lwjgl_stb','lwjgl_vma','lwjgl_shaderc','lwjgl_spvc','jspecify'])
with tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='native-smoke-') as tmp:
    out=pathlib.Path(tmp)
    sources=sorted((ROOT/'java/org/switchcraft/runtime').glob('*.java'))
    subprocess.run([str(javac),'--release','25','-cp',classpath,'-d',str(out),*map(str,sources)],check=True)
    with zipfile.ZipFile(ROOT/'build/switchcraft-native-smoke.jar','w',zipfile.ZIP_DEFLATED) as jar:
        for path in sorted(out.rglob('*.class')):
            entry=zipfile.ZipInfo(path.relative_to(out).as_posix(),(2020,1,1,0,0,0))
            entry.compress_type=zipfile.ZIP_DEFLATED;jar.writestr(entry,path.read_bytes())
print('Built Java 25 JNI/FFM resolver smoke JAR; Horizon execution NOT TESTED')
