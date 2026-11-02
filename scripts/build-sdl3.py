#!/usr/bin/env python3
import hashlib,importlib.util,os,pathlib,shutil,subprocess,tarfile,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1];os.chdir(ROOT)
spec=importlib.util.spec_from_file_location('deps',ROOT/'scripts/bootstrap-deps.py');deps=importlib.util.module_from_spec(spec);spec.loader.exec_module(deps)
cmake=ROOT/'.deps/host-cmake/cmake/data/bin/cmake'
if not cmake.exists():
    with zipfile.ZipFile(deps.download('host_cmake')) as z:z.extractall(ROOT/'.deps/host-cmake')
    for p in (cmake.parent).iterdir():p.chmod(0o755)
source=ROOT/'.deps/sdl3-source';stamp=ROOT/'.deps/sdl3-patch.sha256';patch=ROOT/'patches/sdl3-vulkan-only.patch';digest=hashlib.sha256(patch.read_bytes()).hexdigest()
if not source.exists() or not stamp.exists() or stamp.read_text()!=digest:
    if source.exists():shutil.rmtree(source)
    deps.extract(deps.download('sdl3'),source,True)
    subprocess.run(['patch','--batch','-p1','-i',str(patch)],cwd=source,check=True);stamp.write_text(digest)
dk=pathlib.Path(os.environ.get('DEVKITPRO',str(ROOT/'.toolchain/opt/devkitpro')))
build=ROOT/'build/sdl3'
subprocess.run([str(cmake),'-S',str(source),'-B',str(build),'-G','Unix Makefiles','-DCMAKE_TOOLCHAIN_FILE='+str(dk/'cmake/Switch.cmake'),
    '-DSDL_SHARED=OFF','-DSDL_STATIC=ON','-DSDL_VULKAN=ON','-DSDL_OPENGL=OFF','-DSDL_OPENGLES=OFF','-DSDL_RENDER=OFF','-DSDL_GPU=OFF','-DSDL_TESTS=OFF','-DSDL_EXAMPLES=OFF',
    '-DSDL_SWITCH_VULKAN_LIBRARY='+str(ROOT/'.deps/nvk/lib/libvulkan.a'),'-DCMAKE_BUILD_TYPE=Release','-DCMAKE_INSTALL_PREFIX='+str(ROOT/'.deps/sdl3')],check=True)
subprocess.run([str(cmake),'--build',str(build),'-j4'],check=True);subprocess.run([str(cmake),'--install',str(build)],check=True)
(ROOT/'build/sdl3.stamp').write_text(digest+'\n')
