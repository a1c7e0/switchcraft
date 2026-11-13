"""Execute the packaged Y workload through genuine LWJGL core JNI on the host."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=Path(os.environ.get('JAVA_SWITCH_SOURCE',str(ROOT/'.deps/java-switch')))
JDK=next((ROOT/'.deps/host-jdk25').glob('*/bin'))

class LwjglNativeSmokeTests(unittest.TestCase):
    def test_packaged_workload_calls_core_jni_and_ffm_via_static_provider(self):
        subprocess.run(['python3','scripts/build-lwjgl-core.py','--host'],cwd=ROOT,check=True,capture_output=True)
        with tempfile.TemporaryDirectory() as directory:
            work=Path(directory)
            library=work/'libnative_fixture.so'
            subprocess.run(['gcc','-shared','-fPIC','-std=c11','-Wall','-Wextra','-Werror',
                '-DSC_TEST_LWJGL_CORE','-Iinclude','-I'+str(JAVA/'include'),
                '-I'+str(JDK.parent/'include'),'-I'+str(JDK.parent/'include/linux'),
                'src/native_symbols_jni.c',str(JAVA/'src/native_resolver.c'),'tests/native_symbols_host.c',
                '-Wl,--whole-archive','build/lwjgl-core/host/liblwjgl-core.a','-Wl,--no-whole-archive',
                '-Wl,--exclude-libs,libffi.a','build/lwjgl-core/host/libffi-private/.libs/libffi.a','-ldl','-pthread',
                '-Wl,--no-undefined',
                '-o',str(library)],cwd=ROOT,check=True,capture_output=True)
            source=work/'HostLwjglSmoke.java'
            source.write_text('''public class HostLwjglSmoke {
 public static void main(String[] args) throws Throwable {
  java.lang.foreign.Linker.nativeLinker();
  System.load(args[0]);
  // Select the adapter under test; preserve the actual host architecture/FFM ABI.
  System.setProperty("os.name","Horizon");
  org.switchcraft.runtime.LwjglCoreSmoke.main(new String[0]);
 }
}''')
            jars=[ROOT/'build/switchcraft-lwjgl-horizon.jar',ROOT/'.deps/lwjgl_core.jar',ROOT/'build/switchcraft-native-smoke.jar']
            cp=os.pathsep.join(map(str,[work,*jars]))
            subprocess.run([str(JDK/'javac'),'--release','25','-cp',cp,'-d',str(work),str(source)],check=True,capture_output=True)
            result=subprocess.run([str(JDK/'java'),'--enable-native-access=ALL-UNNAMED',
                '-Dorg.lwjgl.util.NoHashChecks=true','-Dorg.lwjgl.libname=native_fixture',
                '-Djava.library.path='+str(work),'-cp',cp,'HostLwjglSmoke',str(library)],
                cwd=ROOT,text=True,capture_output=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('SWITCHCRAFT_LWJGL_CORE_PASS SDL_version=3004016',result.stdout)
            self.assertIn('SWITCHCRAFT_LWJGL_VULKAN_FFM_PASS apiVersion=',result.stdout)
