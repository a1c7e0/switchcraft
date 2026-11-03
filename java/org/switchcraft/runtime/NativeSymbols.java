package org.switchcraft.runtime;
/** JNI registration is supplied by the embedding Switchcraft process. */
public final class NativeSymbols {
    private NativeSymbols() {}
    public static native boolean moduleAvailable(String module);
    public static native long lookup(String module, String name);
}
