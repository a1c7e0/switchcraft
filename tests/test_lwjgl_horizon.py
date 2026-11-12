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
    def test_real_lwjgl_static_shared_library_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            source=root/'Probe.java'
            source.write_text('''package org.lwjgl.system;
import java.lang.foreign.FunctionDescriptor;
import java.lang.foreign.Linker;
import java.lang.foreign.MemorySegment;
import java.lang.foreign.ValueLayout;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
public class Probe {
 public static void main(String[] args) throws Throwable {
  if (!System.getProperty("os.name").equals("Horizon") || Platform.get()!=Platform.HORIZON ||
      !Platform.get().getName().equals("Horizon") || Platform.getArchitecture()!=Platform.Architecture.X64 ||
      !Platform.get().mapLibraryName("SDL3").equals("SDL3")) throw new AssertionError("platform identity");
  Library.initialize();
  SharedLibrary sdl=Library.loadNative(Probe.class,"org.lwjgl.sdl","SDL3");
  if (!sdl.getName().equals("SDL3") || sdl.getPath()!=null) throw new AssertionError("static library metadata");
  try { sdl.address(); throw new AssertionError("static module fabricated a handle"); }
  catch (UnsupportedOperationException expected) { }

  ByteBuffer name=ByteBuffer.allocateDirect(32);
  name.put("SDL_GetVersion".getBytes(StandardCharsets.UTF_8)).put((byte)0).flip();
  int originalPosition=name.position();
  long address=sdl.getFunctionAddress(name);
  if (address==0 || name.position()!=originalPosition) throw new AssertionError("UTF-8 symbol lookup");
  ByteBuffer missing=ByteBuffer.allocateDirect(12);
  missing.put("missing".getBytes(StandardCharsets.UTF_8)).put((byte)0).flip();
  if (sdl.getFunctionAddress(missing)!=0) throw new AssertionError("missing symbol fabricated");

  Linker linker=Linker.nativeLinker();
  var getVersion=linker.downcallHandle(MemorySegment.ofAddress(address),
      FunctionDescriptor.of(ValueLayout.JAVA_INT));
  int version=(int)getVersion.invokeExact();
  if (version!=30414) throw new AssertionError("FFM SDL_GetVersion="+version);
  sdl.free();
  sdl.close();
  if ((int)getVersion.invokeExact()!=30414) throw new AssertionError("free unloaded process-owned code");

  try { Library.loadNative(Probe.class,"org.lwjgl.opengl","libGLX.so.0");
        throw new AssertionError("unsupported module accepted"); }
  catch (UnsatisfiedLinkError expected) { }
  try { Library.loadNative(Probe.class,"org.lwjgl.sdl","not-SDL3");
        throw new AssertionError("unsupported SDL alias accepted"); }
  catch (UnsatisfiedLinkError expected) { }
  try { Library.loadNative(Probe.class,"org.lwjgl.vulkan","libvulkan.so.1");
        throw new AssertionError("missing static Vulkan module accepted"); }
  catch (UnsatisfiedLinkError expected) {
    if (!expected.getMessage().contains("module unavailable")) throw expected;
  }
  System.out.println("HORIZON STATIC FFM SDL PROVIDER PASS");
 }
}''')
            cp=os.pathsep.join(map(str,[PATCH,CORE,ANNOTATIONS]))
            subprocess.run([str(JDK/'javac'),'--release','25','-cp',cp,'-d',str(root),str(source)],check=True,capture_output=True)
            c=root/'fixture.c'
            c.write_text('''#include <jni.h>
#include <stdint.h>
#include <string.h>
static int SDL_GetVersion(void) { return 30414; }
static int vkGetInstanceProcAddr(void) { return 0; }
static jboolean JNICALL module_available(JNIEnv *env,jclass cls,jstring module) {
  (void)cls; const char *m=(*env)->GetStringUTFChars(env,module,NULL); if(!m)return JNI_FALSE;
  jboolean result=(!strcmp(m,"SDL3"))?JNI_TRUE:JNI_FALSE;
  (*env)->ReleaseStringUTFChars(env,module,m); return result;
}
static jlong JNICALL lookup(JNIEnv *env,jclass cls,jstring module,jstring name) {
  (void)cls; const char *m=(*env)->GetStringUTFChars(env,module,NULL); if(!m)return 0;
  const char *n=(*env)->GetStringUTFChars(env,name,NULL); if(!n){(*env)->ReleaseStringUTFChars(env,module,m);return 0;}
  uintptr_t address=0;
  if(!strcmp(m,"SDL3") && !strcmp(n,"SDL_GetVersion")) address=(uintptr_t)&SDL_GetVersion;
  if(!strcmp(m,"vulkan") && !strcmp(n,"vkGetInstanceProcAddr")) address=(uintptr_t)&vkGetInstanceProcAddr;
  (*env)->ReleaseStringUTFChars(env,name,n);(*env)->ReleaseStringUTFChars(env,module,m);return (jlong)address;
}
JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM *vm,void *reserved) {
  (void)reserved; JNIEnv *env=NULL;
  if((*vm)->GetEnv(vm,(void **)&env,JNI_VERSION_1_8)!=JNI_OK)return JNI_ERR;
  jclass cls=(*env)->FindClass(env,"org/switchcraft/runtime/NativeSymbols");if(!cls)return JNI_ERR;
  JNINativeMethod methods[]={
    {"moduleAvailable","(Ljava/lang/String;)Z",(void *)module_available},
    {"lookup","(Ljava/lang/String;Ljava/lang/String;)J",(void *)lookup}
  };
  jint rc=(*env)->RegisterNatives(env,cls,methods,2);(*env)->DeleteLocalRef(env,cls);
  return rc==JNI_OK?JNI_VERSION_1_8:JNI_ERR;
}''')
            subprocess.run(['gcc','-shared','-fPIC','-I'+str(JDK.parent/'include'),'-I'+str(JDK.parent/'include/linux'),str(c),'-o',str(root/'liblwjgl.so')],check=True,capture_output=True)

            def run(classpath):
                return subprocess.run([str(JDK/'java'),'--enable-native-access=ALL-UNNAMED','-Dos.name=Horizon','-Dos.arch=amd64',
                    '-Djava.library.path='+str(root),'-cp',classpath,'org.lwjgl.system.Probe'],capture_output=True,text=True,timeout=20)

            original=run(os.pathsep.join(map(str,[root,CORE,ANNOTATIONS])))
            self.assertNotEqual(original.returncode,0)
            self.assertIn('Unknown platform: Horizon',original.stderr)
            patched=run(os.pathsep.join(map(str,[root,PATCH,CORE,ANNOTATIONS])))
            self.assertEqual(patched.returncode,0,patched.stdout+patched.stderr)
            self.assertIn('HORIZON STATIC FFM SDL PROVIDER PASS',patched.stdout)


if __name__=='__main__':
    unittest.main()
