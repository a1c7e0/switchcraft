"""Incidental GL classes must not load an unavailable driver on Vulkan Horizon."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
JDK=next((ROOT/'.deps/host-jdk25').glob('*/bin'))

class DeferredGlTests(unittest.TestCase):
    def test_horizon_can_import_gl_classes_and_rejects_real_gl_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            work=Path(directory)
            source=work/'DeferredGl.java'
            source.write_text('''public class DeferredGl {
 public static void main(String[] args) throws Exception {
  if (!org.lwjgl.system.Platform.get().name().equals("HORIZON")) throw new AssertionError();
  Class.forName("org.lwjgl.opengl.GL");
  Class.forName("org.lwjgl.opengl.GL11");
  if (!org.lwjgl.system.Configuration.OPENGL_EXPLICIT_INIT.get(false)) throw new AssertionError();
  try { org.lwjgl.opengl.GL.create(); throw new AssertionError("OpenGL was incorrectly accepted"); }
  catch (UnsupportedOperationException expected) { }
  System.out.println("Horizon deferred GL import: PASS; OpenGL creation remains unsupported");
 }
}''')
            jars=[ROOT/'build/switchcraft-lwjgl-horizon.jar',ROOT/'.deps/lwjgl_core.jar',ROOT/'.deps/lwjgl_opengl.jar']
            cp=os.pathsep.join(map(str,[work,*jars]))
            subprocess.run([str(JDK/'javac'),'--release','25','-cp',cp,'-d',str(work),str(source)],check=True,capture_output=True)
            result=subprocess.run([str(JDK/'java'),'-Dos.name=Horizon','-Dorg.lwjgl.libname=java',
                '--enable-native-access=ALL-UNNAMED','-cp',cp,'DeferredGl'],cwd=ROOT,text=True,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('deferred GL import: PASS',result.stdout)
