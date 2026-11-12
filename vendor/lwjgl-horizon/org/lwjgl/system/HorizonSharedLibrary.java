/*
 * Copyright LWJGL. All rights reserved.
 * License terms: https://www.lwjgl.org/license
 */
package org.lwjgl.system;

import org.jspecify.annotations.Nullable;
import org.switchcraft.runtime.NativeSymbols;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;

/**
 * LWJGL FunctionProvider backed by Switchcraft's process-lifetime static modules.
 * This class intentionally exposes only the library aliases used by LWJGL 3.4.3.
 */
final class HorizonSharedLibrary implements SharedLibrary {

    private final String module;
    private final String name;

    private HorizonSharedLibrary(String module, String name) {
        this.module = module;
        this.name = name;
    }

    static SharedLibrary load(String lwjglModule, String libraryName) {
        String module;
        if ("org.lwjgl.sdl".equals(lwjglModule) && "SDL3".equals(libraryName)) {
            module = "SDL3";
        } else if ("org.lwjgl.vulkan".equals(lwjglModule) && "libvulkan.so.1".equals(libraryName)) {
            module = "vulkan";
        } else {
            throw new UnsatisfiedLinkError("Unsupported Horizon static FFM library: " + lwjglModule + "/" + libraryName);
        }

        if (!NativeSymbols.moduleAvailable(module)) {
            throw new UnsatisfiedLinkError("Horizon static FFM module unavailable: " + module);
        }
        return new HorizonSharedLibrary(module, libraryName);
    }

    @Override
    public long getFunctionAddress(ByteBuffer functionName) {
        String symbol = decodeSymbol(functionName);
        return symbol == null ? 0L : NativeSymbols.lookup(module, symbol);
    }

    private static @Nullable String decodeSymbol(ByteBuffer source) {
        if (source == null) {
            return null;
        }

        ByteBuffer bytes = source.duplicate().order(ByteOrder.nativeOrder());
        int start = bytes.position();
        int end = start;
        while (end < bytes.limit() && bytes.get(end) != 0) {
            end++;
        }
        if (end == bytes.limit()) {
            return null; // LWJGL symbol buffers are expected to be NUL terminated.
        }

        bytes.position(start);
        bytes.limit(end);
        try {
            return StandardCharsets.UTF_8.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT)
                .decode(bytes)
                .toString();
        } catch (CharacterCodingException ignored) {
            return null;
        }
    }

    @Override
    public String getName() {
        return name;
    }

    @Override
    public @Nullable String getPath() {
        return null; // Static linked code has no filesystem path.
    }

    @Override
    public long address() {
        throw new UnsupportedOperationException("A static Horizon module has no library handle");
    }

    @Override
    public void free() {
        // Code and function addresses belong to the process and cannot be unloaded.
    }
}
