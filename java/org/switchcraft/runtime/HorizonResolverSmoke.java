package org.switchcraft.runtime;
import java.lang.foreign.FunctionDescriptor;
import java.lang.foreign.Linker;
import java.lang.foreign.MemorySegment;
import java.lang.foreign.ValueLayout;
/** Calls real resolved function addresses; no SDL window or Minecraft is started. */
public final class HorizonResolverSmoke {
    public static void main(String[] args) throws Throwable {
        if (!NativeSymbols.moduleAvailable("SDL3") || !NativeSymbols.moduleAvailable("vulkan"))
            throw new UnsatisfiedLinkError("SDL3 or vulkan static module unavailable");
        long address=NativeSymbols.lookup("SDL3","SDL_GetVersion");
        if (address==0 || NativeSymbols.lookup("vulkan","vkGetInstanceProcAddr")==0)
            throw new UnsatisfiedLinkError("Required SDL/Vulkan symbol unavailable");
        if (NativeSymbols.moduleAvailable("missing-module") || NativeSymbols.lookup("SDL3","missing-symbol")!=0)
            throw new AssertionError("Missing native was incorrectly reported available");
        int version=(int)Linker.nativeLinker().downcallHandle(MemorySegment.ofAddress(address),
            FunctionDescriptor.of(ValueLayout.JAVA_INT)).invokeExact();
        if (version/1000000!=3) throw new AssertionError("Unexpected SDL major: "+version);
        System.out.println("SWITCHCRAFT_SDL_FFM_PASS SDL_version="+version);
    }
}
