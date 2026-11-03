import os
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
JAVA=Path(os.environ.get('JAVA_SWITCH_SOURCE',str(ROOT/'.deps/java-switch')))
JDK=next((ROOT/'.deps/host-jdk25').glob('*/bin'))
class NativeSymbolsJniTests(unittest.TestCase):
    def test_real_jni_registration_and_ffm_downcall_through_sdk(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); library=root/'libnative_fixture.so'
            subprocess.run(['gcc','-shared','-fPIC','-std=c11','-Wall','-Wextra','-Werror',
                '-Iinclude','-I'+str(JAVA/'include'),'-I'+str(JDK.parent/'include'),'-I'+str(JDK.parent/'include/linux'),
                'src/native_symbols_jni.c',str(JAVA/'src/native_resolver.c'),'tests/native_symbols_host.c',
                '-o',str(library)],cwd=ROOT,check=True,capture_output=True)
            src=root/'HostSmoke.java';src.write_text('''public class HostSmoke {
 public static void main(String[] args) throws Throwable {
  System.load(args[0]); org.switchcraft.runtime.HorizonResolverSmoke.main(new String[0]);
 }}''')
            jar=ROOT/'build/switchcraft-native-smoke.jar'
            subprocess.run([str(JDK/'javac'),'--release','25','-cp',str(jar),'-d',str(root),str(src)],check=True,capture_output=True)
            p=subprocess.run([str(JDK/'java'),'--enable-native-access=ALL-UNNAMED','-cp',str(root)+os.pathsep+str(jar),
                'HostSmoke',str(library)],text=True,capture_output=True,timeout=30)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            self.assertIn('SWITCHCRAFT_SDL_FFM_PASS SDL_version=3004016',p.stdout)
