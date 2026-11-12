"""Reference the pinned LWJGL core jar against genuine upstream JNI C."""
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
JDK = ROOT / ".deps/host-jdk25/jdk-25.0.5+8/bin"


class TestLWJGLCore(unittest.TestCase):
    def test_pinned_lwjgl_jar_calls_real_upstream_core_jni(self):
        subprocess.run(["python3", str(ROOT / "scripts/build-lwjgl-core.py"), "--host"], cwd=ROOT, check=True)
        with tempfile.TemporaryDirectory(prefix="lwjgl-core-java-") as tmp:
            tmp = pathlib.Path(tmp)
            probe = tmp / "lwjgl_core_probe.c"
            probe.write_text("""#include <jni.h>
#include <stdint.h>
#include <switchcraft/lwjgl_core.h>

typedef jint (JNICALL *lwjgl_onload_fn)(JavaVM *, void *);
typedef void (JNICALL *lwjgl_onunload_fn)(JavaVM *, void *);

JNIEXPORT jint JNICALL Java_LwjglCoreReference_checkProvider(JNIEnv *env, jclass cls) {
    (void)cls;
    if (!sc_lwjgl_core_available("lwjgl") || sc_lwjgl_core_available("LWJGL") ||
        sc_lwjgl_core_available("not-lwjgl")) return 1;
    uintptr_t named = sc_lwjgl_core_lookup("lwjgl", "JNI_OnLoad_lwjgl");
    uintptr_t global = sc_lwjgl_core_lookup(NULL, "JNI_OnLoad_lwjgl");
    uintptr_t unload = sc_lwjgl_core_lookup("lwjgl", "JNI_OnUnload_lwjgl");
    if (!named || named != global || !unload) return 2;
    if (sc_lwjgl_core_lookup("not-lwjgl", "JNI_OnLoad_lwjgl") ||
        sc_lwjgl_core_lookup("lwjgl", "JNI_OnLoad_missing") ||
        sc_lwjgl_core_lookup(NULL, "JNI_OnLoad_missing")) return 3;
    JavaVM *vm = NULL;
    if ((*env)->GetJavaVM(env, &vm) != JNI_OK || vm == NULL) return 4;
    if (((lwjgl_onload_fn)named)(vm, NULL) != JNI_VERSION_1_8) return 5;
    ((lwjgl_onunload_fn)unload)(vm, NULL);
    return 0;
}
""")
            host_jni = ROOT / ".deps/host-jdk25/jdk-25.0.5+8/include"
            host_cc = subprocess.check_output(["cc", "-print-prog-name=cc"], text=True).strip()
            probe_library = ROOT / "build/lwjgl-core/host/liblwjgl_probe.so"
            subprocess.run([host_cc, "-std=c11", "-fPIC", "-shared",
                            "-I", str(host_jni), "-I", str(host_jni / "linux"),
                            "-I", str(ROOT / "include"), str(probe),
                            "-L", str(ROOT / "build/lwjgl-core/host"),
                            f"-Wl,-rpath,{ROOT / 'build/lwjgl-core/host'}", "-llwjgl",
                            "-o", str(probe_library)], check=True)
            source = tmp / "LwjglCoreReference.java"
            source.write_text("""import java.lang.foreign.Arena;
import java.lang.foreign.Linker;
import java.lang.foreign.FunctionDescriptor;
import java.lang.foreign.MemorySegment;
import java.lang.foreign.ValueLayout;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;
import org.lwjgl.system.JNI;
import org.lwjgl.system.MemoryUtil;
import org.lwjgl.system.libc.LibCErrno;
import org.lwjgl.system.libc.LibCLocale;
import org.lwjgl.system.libc.LibCStdio;
import org.lwjgl.system.libc.LibCString;
import org.lwjgl.system.libffi.LibFFI;
import org.lwjgl.system.jni.JNINativeInterface;

public class LwjglCoreReference {
    private static native int checkProvider();
    private static int marker() { return 0x51A7; }
    public static void main(String[] args) throws Throwable {
        System.loadLibrary("lwjgl");
        System.loadLibrary("lwjgl_probe");
        if (checkProvider() != 0) throw new AssertionError("provider lookup or JNI_OnLoad_lwjgl check failed");
        try (Arena arena = Arena.ofConfined()) {
            long p = MemoryUtil.nmemAlloc(8);
            if (p == 0) throw new AssertionError("upstream allocator returned null");
            try {
                MemoryUtil.memPutInt(p, 0x12345678);
                if (MemoryUtil.memGetInt(p) != 0x12345678) throw new AssertionError("native read/write mismatch");
            } finally { MemoryUtil.nmemFree(p); }

            var text = arena.allocateFrom("portable libc JNI");
            if (LibCString.nstrlen(text.address()) != 17) throw new AssertionError("libc strlen JNI mismatch");
            if (LibCErrno.errno() < 0) throw new AssertionError("errno JNI returned a negative value");
            if (LibCLocale.LC_ALL < 0 || LibCStdio.stdout == 0 || LibCStdio.nfflush(LibCStdio.stdout) != 0)
                throw new AssertionError("libc locale/stdio JNI mismatch");
            if (JNINativeInterface.GetVersion() < 0x00010008)
                throw new AssertionError("JNI function table access mismatch");
            if (LibFFI.FFI_VERSION_NUMBER < 30800 ||
                LibFFI.ffi_get_default_abi() != LibFFI.FFI_DEFAULT_ABI)
                throw new AssertionError("libffi version/default ABI mismatch");

            MemorySegment stub = Linker.nativeLinker().upcallStub(
                MethodHandles.lookup().findStatic(LwjglCoreReference.class, "marker", MethodType.methodType(int.class)),
                FunctionDescriptor.of(ValueLayout.JAVA_INT), arena);
            if (JNI.invokeI(stub.address()) != 0x51A7) throw new AssertionError("JNI.invokeI dispatch mismatch");
        }
        System.out.println("LWJGL 3.4.3 pinned jar genuine core JNI calls passed");
    }
}
""")
            jar = ROOT / ".deps/lwjgl_core.jar"
            subprocess.run([str(JDK / "javac"), "--release", "25", "-cp", str(jar), "-d", str(tmp), str(source)], check=True)
            subprocess.run([str(JDK / "java"), "--enable-native-access=ALL-UNNAMED",
                            "-Dorg.lwjgl.util.NoHashChecks=true",
                            f"-Djava.library.path={ROOT / 'build/lwjgl-core/host'}",
                            "-cp", f"{jar}:{tmp}", "LwjglCoreReference"], cwd=ROOT, check=True)


if __name__ == "__main__":
    unittest.main()
