package org.switchcraft.launcher;
import java.lang.instrument.*;
import java.security.ProtectionDomain;
/** Restricts one pinned renderer method, without replacing the game class loader. */
public final class VulkanOnlyAgent {
    public static void premain(String args,Instrumentation instrumentation){
        instrumentation.addTransformer(new ClassFileTransformer(){
            public byte[] transform(ClassLoader loader,String name,Class<?> cls,ProtectionDomain domain,byte[] bytes){
                if(!VulkanOnlyTransform.TARGET.replace('.','/').equals(name))return null;
                try{return VulkanOnlyTransform.restrict(bytes);}
                catch(Throwable error){System.err.println("[Switchcraft] Vulkan-only profile rejected: "+error);return new byte[]{0};}
            }
        });
    }
}
