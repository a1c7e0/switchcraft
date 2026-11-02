package org.switchcraft.launcher;

import java.security.*;
import java.util.*;
import java.lang.classfile.*;
import java.lang.constant.*;

/** Restricts the renderer method; changes no account or authentication code. */
public final class VulkanOnlyTransform {
    static final String TARGET="net.minecraft.client.PreferredGraphicsApi";
    static final String EXPECTED="b42d53d78fba06b0fbdb90395dfdc065f319dce9dc037fa4184f9399078ed7ee";
    static byte[] restrict(byte[] original)throws Exception {
        String hash=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(original));
        if(!EXPECTED.equals(hash))throw new SecurityException("Snapshot renderer class differs from pinned snapshot 6");
        byte[] result=rewrite(original);
        System.out.println("[Switchcraft] VULKAN_ONLY_APPLIED target=26.4-snapshot-6 original_sha256="+hash);
        return result;
    }
    static byte[] rewrite(byte[] original){
        boolean[] changed={false};
        ClassDesc backend=ClassDesc.of("com.mojang.renderpearl.api.device.GpuBackend");
        ClassDesc vulkan=ClassDesc.of("com.mojang.renderpearl.backend.vulkan.VulkanBackend");
        ClassFile cf=ClassFile.of();
        byte[] result=cf.transformClass(cf.parse(original),(builder,element)->{
            if(element instanceof MethodModel method&&method.methodName().equalsString("getBackendsToTry")&&method.methodType().equalsString("()[Lcom/mojang/renderpearl/api/device/GpuBackend;")){
                changed[0]=true;
                builder.withMethodBody(method.methodName(),method.methodType(),method.flags().flagsMask(),code->code.iconst_1().anewarray(backend).dup().iconst_0()
                    .new_(vulkan).dup().invokespecial(vulkan,"<init>",MethodTypeDesc.of(ConstantDescs.CD_void)).aastore().areturn());
            }else builder.with(element);
        });
        if(!changed[0])throw new IllegalStateException("Pinned renderer method missing");
        return result;
    }
}
