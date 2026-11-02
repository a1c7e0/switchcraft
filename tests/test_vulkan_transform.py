import os,pathlib,subprocess,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class VulkanTransformTests(unittest.TestCase):
    def test_renderer_is_single_vulkan_and_wrong_hash_is_rejected(self):
        java_root=pathlib.Path(os.environ.get('JAVA_SWITCH_SOURCE',str(ROOT/'.deps/java-switch')))
        jdk=next((java_root/'.deps/host-jdk25').glob('*/bin'))
        # Original synthetic fixtures: no Mojang class bytes or game JAR needed.
        sources={
          'com/mojang/renderpearl/api/device/GpuBackend.java':'package com.mojang.renderpearl.api.device; public interface GpuBackend {}',
          'com/mojang/renderpearl/backend/vulkan/VulkanBackend.java':'package com.mojang.renderpearl.backend.vulkan; public class VulkanBackend implements com.mojang.renderpearl.api.device.GpuBackend {}',
          'com/mojang/renderpearl/backend/opengl/GlBackend.java':'package com.mojang.renderpearl.backend.opengl; public class GlBackend implements com.mojang.renderpearl.api.device.GpuBackend {public GlBackend(){throw new AssertionError("OpenGL instantiated");}}',
          'net/minecraft/client/PreferredGraphicsApi.java':'package net.minecraft.client; public class PreferredGraphicsApi {public com.mojang.renderpearl.api.device.GpuBackend[] getBackendsToTry(){return new com.mojang.renderpearl.api.device.GpuBackend[]{new com.mojang.renderpearl.backend.opengl.GlBackend(),new com.mojang.renderpearl.backend.vulkan.VulkanBackend()};}}',
          'org/switchcraft/launcher/TransformTest.java':'''package org.switchcraft.launcher;
import java.nio.file.*;import java.net.*;
public class TransformTest {
 public static void main(String[] a)throws Exception{
  Path file=Path.of(a[0],"net/minecraft/client/PreferredGraphicsApi.class");byte[] original=Files.readAllBytes(file);
  boolean rejected=false;try{VulkanOnlyTransform.restrict(original);}catch(SecurityException expected){rejected=true;}
  if(!rejected)throw new AssertionError("Wrong snapshot hash accepted");
  Files.write(file,VulkanOnlyTransform.rewrite(original));
  try(URLClassLoader loader=new URLClassLoader(new URL[]{Path.of(a[0]).toUri().toURL()},null)){
   Class<?> type=loader.loadClass("net.minecraft.client.PreferredGraphicsApi");
   Object[] backends=(Object[])type.getMethod("getBackendsToTry").invoke(type.getConstructor().newInstance());
   if(backends.length!=1||!backends[0].getClass().getName().endsWith("VulkanBackend"))throw new AssertionError("Renderer not strictly Vulkan");
  }System.out.println("STRICT VULKAN TRANSFORM PASS");
 }
}'''}
        with tempfile.TemporaryDirectory() as tmp:
            base=pathlib.Path(tmp);files=[]
            for name,source in sources.items():
                path=base/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(source);files.append(str(path))
            cp=str(ROOT/'build/switchcraft-launcher-bridge.jar')
            subprocess.run([str(jdk/'javac'),'--release','25','-cp',cp,'-d',str(base),*files],check=True,capture_output=True)
            p=subprocess.run([str(jdk/'java'),'-cp',cp+os.pathsep+str(base),'org.switchcraft.launcher.TransformTest',str(base)],capture_output=True,text=True,timeout=20)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertIn('STRICT VULKAN TRANSFORM PASS',p.stdout)

    def test_verified_official_snapshot_class(self):
        import hashlib, zipfile
        supplied=os.environ.get('SWITCHCRAFT_CLIENT_JAR')
        if not supplied:self.skipTest('set SWITCHCRAFT_CLIENT_JAR to the owned, verified snapshot client')
        client=pathlib.Path(supplied)
        self.assertEqual(hashlib.sha1(client.read_bytes()).hexdigest(),'8a97d5dafe80783525a2807b220527b65df724a5')
        with zipfile.ZipFile(client) as archive:
            original=archive.read('net/minecraft/client/PreferredGraphicsApi.class')
        self.assertEqual(hashlib.sha256(original).hexdigest(),'b42d53d78fba06b0fbdb90395dfdc065f319dce9dc037fa4184f9399078ed7ee')
        java_root=pathlib.Path(os.environ.get('JAVA_SWITCH_SOURCE',str(ROOT/'.deps/java-switch')))
        jdk=next((java_root/'.deps/host-jdk25').glob('*/bin'))
        with tempfile.TemporaryDirectory() as tmp:
            base=pathlib.Path(tmp);src=base/'OfficialTransformTest.java'
            src.write_text('''package org.switchcraft.launcher;
import java.nio.file.*;
public class OfficialTransformTest { public static void main(String[] args) throws Exception {
 Files.write(Path.of(args[1]), VulkanOnlyTransform.restrict(Files.readAllBytes(Path.of(args[0]))));
}}''')
            original_file=base/'original.class';transformed=base/'PreferredGraphicsApi.class';original_file.write_bytes(original)
            cp=str(ROOT/'build/switchcraft-launcher-bridge.jar')
            subprocess.run([str(jdk/'javac'),'--release','25','-cp',cp,'-d',str(base),str(src)],check=True,capture_output=True)
            subprocess.run([str(jdk/'java'),'-cp',cp+os.pathsep+str(base),'org.switchcraft.launcher.OfficialTransformTest',str(original_file),str(transformed)],check=True,capture_output=True)
            output=subprocess.check_output([str(jdk/'javap'),'-c','-p',str(transformed)],text=True)
            import re
            method=re.search(r'getBackendsToTry\(\).*?Code:(.*?)(?:\n\s*(?:public|private|protected|static)\s|\n})',output,re.S)
            self.assertIsNotNone(method,output)
            self.assertIn('vulkan/VulkanBackend',method.group(1))
            self.assertNotIn('opengl/',method.group(1))
