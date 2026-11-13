package org.switchcraft.runtime;

import java.lang.foreign.Arena;
import java.lang.foreign.FunctionDescriptor;
import java.lang.foreign.Linker;
import java.lang.foreign.MemorySegment;
import java.lang.foreign.ValueLayout;
import org.lwjgl.system.JNI;
import org.lwjgl.system.Library;
import org.lwjgl.system.MemoryUtil;
import org.lwjgl.system.SharedLibrary;

/** Real native prerequisites for Minecraft, without starting a game or window. */
public final class LwjglCoreSmoke {
    public static void main(String[] args) throws Throwable {
        if (!NativeSymbols.moduleAvailable("lwjgl"))
            throw new UnsatisfiedLinkError("Genuine LWJGL core provider is not linked");
        Library.initialize();
        long memory = MemoryUtil.nmemAllocChecked(16);
        try {
            MemoryUtil.memPutLong(memory, 0x123456789abcdef0L);
            if (MemoryUtil.memGetLong(memory) != 0x123456789abcdef0L)
                throw new AssertionError("LWJGL native allocation/readback mismatch");
        } finally {
            MemoryUtil.nmemFree(memory);
        }
        try (SharedLibrary sdl = Library.loadNative(LwjglCoreSmoke.class, "org.lwjgl.sdl", "SDL3");
             SharedLibrary vulkan = Library.loadNative(LwjglCoreSmoke.class, "org.lwjgl.vulkan", "libvulkan.so.1");
             Arena arena = Arena.ofConfined()) {
            long getVersion = sdl.getFunctionAddress("SDL_GetVersion");
            if (getVersion == 0 || sdl.getFunctionAddress("switchcraft_missing_symbol") != 0)
                throw new AssertionError("SDL static function lookup mismatch");
            int jniVersion = JNI.invokeI(getVersion);
            int ffmVersion = (int)Linker.nativeLinker().downcallHandle(
                MemorySegment.ofAddress(getVersion), FunctionDescriptor.of(ValueLayout.JAVA_INT)).invokeExact();
            if (jniVersion != ffmVersion || jniVersion / 1000000 != 3)
                throw new AssertionError("LWJGL JNI/FFM SDL version mismatch");
            System.out.println("SWITCHCRAFT_LWJGL_CORE_PASS SDL_version=" + jniVersion);

            long getProcAddress = vulkan.getFunctionAddress("vkGetInstanceProcAddr");
            if (getProcAddress == 0)
                throw new UnsatisfiedLinkError("vkGetInstanceProcAddr is unavailable");
            MemorySegment enumerate = (MemorySegment)Linker.nativeLinker().downcallHandle(
                MemorySegment.ofAddress(getProcAddress),
                FunctionDescriptor.of(ValueLayout.ADDRESS, ValueLayout.ADDRESS, ValueLayout.ADDRESS))
                .invokeExact(MemorySegment.NULL, arena.allocateFrom("vkEnumerateInstanceVersion"));
            if (enumerate.equals(MemorySegment.NULL))
                throw new UnsatisfiedLinkError("Vulkan instance version entry point is unavailable");
            MemorySegment version = arena.allocate(ValueLayout.JAVA_INT);
            int result = (int)Linker.nativeLinker().downcallHandle(enumerate,
                FunctionDescriptor.of(ValueLayout.JAVA_INT, ValueLayout.ADDRESS)).invokeExact(version);
            if (result != 0 || version.get(ValueLayout.JAVA_INT, 0) < (1 << 22))
                throw new AssertionError("Vulkan instance version query failed: " + result);
            System.out.println("SWITCHCRAFT_LWJGL_VULKAN_FFM_PASS apiVersion=" + version.get(ValueLayout.JAVA_INT, 0));
        }
    }
}
