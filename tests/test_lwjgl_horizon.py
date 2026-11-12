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
import java.util.function.Supplier;
public class Probe {
 static void unsupported(Supplier<String[]> method) {
  try { method.get(); throw new AssertionError("unsupported desktop library name fabricated"); }
  catch (UnsupportedOperationException expected) { }
 }
 public static void main(String[] args) throws Throwable {
  if (!System.getProperty("os.name").equals("Horizon") || Platform.get()!=Platform.HORIZON ||
      !Platform.get().getName().equals("Horizon") || Platform.getArchitecture()!=Platform.Architecture.X64 ||
      !Platform.get().mapLibraryName("SDL3").equals("SDL3")) throw new AssertionError("platform identity");
  boolean expectedExplicit=Boolean.parseBoolean(args[0]);
  if (!Configuration.OPENGL_EXPLICIT_INIT.get(false).equals(expectedExplicit))
      throw new AssertionError("OpenGL explicit-init policy");
  unsupported(Configuration::EGL_LIBRARY_NAME_DEFAULTS);
  unsupported(Configuration::OPENGL_LIBRARY_NAME_DEFAULTS);
  unsupported(Configuration::OPENGL_OSMESA_LIBRARY_NAME_DEFAULTS);
  unsupported(Configuration::OPENGLES_LIBRARY_NAME_DEFAULTS);
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
  String[][] aliases={
      {"org.lwjgl.vulkan","libvulkan.so.1","vulkan","vkGetInstanceProcAddr"},
      {"org.lwjgl.freetype","freetype","freetype","FT_Init_FreeType"},
      {"org.lwjgl.openal","openal","openal","alcGetString"},
      {"org.lwjgl.shaderc","shaderc","shaderc","shaderc_compiler_initialize"},
      {"org.lwjgl.spvc","spirv-cross","spirv-cross-c","spvc_context_create"}
  };
  for (String[] alias:aliases) {
      SharedLibrary library=Library.loadNative(Probe.class,alias[0],alias[1]);
      byte[] encoded=alias[3].getBytes(StandardCharsets.UTF_8);
      ByteBuffer aliasName=ByteBuffer.allocate(encoded.length+1).put(encoded).put((byte)0); aliasName.flip();
      if (library.getFunctionAddress(aliasName)==0)
          throw new AssertionError("static module alias "+alias[2]);
  }
  System.setProperty("fixture.missingModule","SDL3");
  try { Library.loadNative(Probe.class,"org.lwjgl.sdl","SDL3");
        throw new AssertionError("missing static module accepted"); }
  catch (UnsatisfiedLinkError expected) {
    if (!expected.getMessage().contains("module unavailable")) throw expected;
  }
  System.clearProperty("fixture.missingModule");
  sdl.free();
  sdl.close();
  if ((int)getVersion.invokeExact()!=30414) throw new AssertionError("free unloaded process-owned code");

  try { Library.loadNative(Probe.class,"org.lwjgl.opengl","libGLX.so.0");
        throw new AssertionError("unsupported module accepted"); }
  catch (UnsatisfiedLinkError expected) { }
  try { Library.loadNative(Probe.class,"org.lwjgl.sdl","not-SDL3");
        throw new AssertionError("unsupported SDL alias accepted"); }
  catch (UnsatisfiedLinkError expected) { }
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
static int generic_symbol(void) { return 1; }
static jboolean JNICALL module_available(JNIEnv *env,jclass cls,jstring module) {
  (void)cls; const char *m=(*env)->GetStringUTFChars(env,module,NULL); if(!m)return JNI_FALSE;
  jboolean result=(!strcmp(m,"SDL3") || !strcmp(m,"vulkan") || !strcmp(m,"freetype") ||
                   !strcmp(m,"openal") || !strcmp(m,"shaderc") || !strcmp(m,"spirv-cross-c"))?JNI_TRUE:JNI_FALSE;
  jclass system=(*env)->FindClass(env,"java/lang/System");
  jmethodID get_property=system?(*env)->GetStaticMethodID(env,system,"getProperty","(Ljava/lang/String;)Ljava/lang/String;"):NULL;
  if(get_property){
    jstring key=(*env)->NewStringUTF(env,"fixture.missingModule");
    jstring missing=(jstring)(*env)->CallStaticObjectMethod(env,system,get_property,key);
    if(missing){const char *v=(*env)->GetStringUTFChars(env,missing,NULL);if(v){if(!strcmp(v,m))result=JNI_FALSE;(*env)->ReleaseStringUTFChars(env,missing,v);}(*env)->DeleteLocalRef(env,missing);}
    if(key)(*env)->DeleteLocalRef(env,key);(*env)->DeleteLocalRef(env,system);
  }
  (*env)->ReleaseStringUTFChars(env,module,m); return result;
}
static jlong JNICALL lookup(JNIEnv *env,jclass cls,jstring module,jstring name) {
  (void)cls; const char *m=(*env)->GetStringUTFChars(env,module,NULL); if(!m)return 0;
  const char *n=(*env)->GetStringUTFChars(env,name,NULL); if(!n){(*env)->ReleaseStringUTFChars(env,module,m);return 0;}
  uintptr_t address=0;
  if(!strcmp(m,"SDL3") && !strcmp(n,"SDL_GetVersion")) address=(uintptr_t)&SDL_GetVersion;
  if(!strcmp(m,"vulkan") && !strcmp(n,"vkGetInstanceProcAddr")) address=(uintptr_t)&vkGetInstanceProcAddr;
  if((!strcmp(m,"freetype") && !strcmp(n,"FT_Init_FreeType")) ||
     (!strcmp(m,"openal") && !strcmp(n,"alcGetString")) ||
     (!strcmp(m,"shaderc") && !strcmp(n,"shaderc_compiler_initialize")) ||
     (!strcmp(m,"spirv-cross-c") && !strcmp(n,"spvc_context_create"))) address=(uintptr_t)&generic_symbol;
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

            def run(classpath, expected_explicit, explicit_property=None):
                command=[str(JDK/'java'),'--enable-native-access=ALL-UNNAMED','-Dos.name=Horizon','-Dos.arch=amd64']
                if explicit_property is not None:
                    command.append('-Dorg.lwjgl.opengl.explicitInit='+explicit_property)
                command += ['-Djava.library.path='+str(root),'-cp',classpath,'org.lwjgl.system.Probe',str(expected_explicit).lower()]
                return subprocess.run(command,capture_output=True,text=True,timeout=20)

            original=run(os.pathsep.join(map(str,[root,CORE,ANNOTATIONS])),True)
            self.assertNotEqual(original.returncode,0)
            self.assertIn('Unknown platform: Horizon',original.stderr)
            patched_cp=os.pathsep.join(map(str,[root,PATCH,CORE,ANNOTATIONS]))
            patched=run(patched_cp,True)
            self.assertEqual(patched.returncode,0,patched.stdout+patched.stderr)
            explicit_override=run(patched_cp,False,'false')
            self.assertEqual(explicit_override.returncode,0,explicit_override.stdout+explicit_override.stderr)
            self.assertIn('HORIZON STATIC FFM SDL PROVIDER PASS',patched.stdout)


if __name__=='__main__':
    unittest.main()
