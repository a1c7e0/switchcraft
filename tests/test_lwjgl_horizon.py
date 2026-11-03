import os
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
JDK=next((ROOT/'.deps/host-jdk25').glob('*/bin'))
CORE=ROOT/'.deps/lwjgl_core.jar'
ANNOTATIONS=ROOT/'.deps/jspecify.jar'
PATCH=ROOT/'build/switchcraft-lwjgl-horizon.jar'
class LwjglHorizonTests(unittest.TestCase):
    def test_real_lwjgl_platform_and_fail_closed_library_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'Probe.java'
            source.write_text('''package org.lwjgl.system;
import java.util.concurrent.atomic.AtomicReference;
public class Probe {
 public static void main(String[] args) {
  if (!System.getProperty("os.name").equals("Horizon") || Platform.get()!=Platform.HORIZON ||
      !Platform.get().getName().equals("Horizon") || Platform.getArchitecture()!=Platform.Architecture.ARM64 ||
      !Platform.get().mapLibraryName("SDL3").equals("SDL3")) throw new AssertionError("platform identity");
  Library.initialize();
  AtomicReference<String> called = new AtomicReference<>();
  Library.loadSystem(name -> {throw new AssertionError("desktop path loader called");}, called::set,
      Probe.class,"org.lwjgl.test","actual-static-module");
  if (!"actual-static-module".equals(called.get())) throw new AssertionError("module forwarding");
  try { Library.loadNative(Probe.class,"org.lwjgl.test","missing-module"); throw new AssertionError("fabricated native library"); }
  catch (UnsatisfiedLinkError expected) {
   if (!expected.getMessage().contains("Horizon static FFM library adapter unavailable")) throw expected;
  }
  System.out.println("HORIZON PLATFORM AND FAIL-CLOSED LIBRARY PASS");
 }
}''')
            cp=os.pathsep.join(map(str,[PATCH,CORE,ANNOTATIONS]))
            subprocess.run([str(JDK/'javac'),'--release','25','-cp',cp,'-d',str(root),str(source)],check=True,capture_output=True)
            c=root/'fixture.c';c.write_text('#include <jni.h>\nJNIEXPORT jint JNICALL JNI_OnLoad(JavaVM *vm, void *r) {(void)vm;(void)r;return JNI_VERSION_1_8;}\n')
            subprocess.run(['gcc','-shared','-fPIC','-I'+str(JDK.parent/'include'),'-I'+str(JDK.parent/'include/linux'),str(c),'-o',str(root/'liblwjgl.so')],check=True,capture_output=True)
            def run(classpath):
                return subprocess.run([str(JDK/'java'),'--enable-native-access=ALL-UNNAMED','-Dos.name=Horizon','-Dos.arch=aarch64',
                    '-Djava.library.path='+str(root),'-cp',classpath,'org.lwjgl.system.Probe'],capture_output=True,text=True,timeout=20)
            original=run(os.pathsep.join(map(str,[root,CORE,ANNOTATIONS])))
            self.assertNotEqual(original.returncode,0)
            self.assertIn('Unknown platform: Horizon',original.stderr)
            patched=run(os.pathsep.join(map(str,[PATCH,root,CORE,ANNOTATIONS])))
            self.assertEqual(patched.returncode,0,patched.stdout+patched.stderr)
            self.assertIn('HORIZON PLATFORM AND FAIL-CLOSED LIBRARY PASS',patched.stdout)
