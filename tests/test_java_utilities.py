#!/usr/bin/env python3
"""Run pinned LWJGL STB, Shaderc and SPIRV-Cross Java APIs on Linux."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
JDK = next((ROOT / ".deps/host-jdk25").glob("*/bin"))
SDK = ROOT / "build/java25-integrated/sdk"
RUNTIME = ROOT / "build/java25-integrated/runtime/openjdk25-horizon-runtime"
JAVA_SWITCH_SOURCE = Path(os.environ.get("JAVA_SWITCH_SOURCE", ROOT / ".deps/java-switch"))
SHADER_BUILD = Path(os.environ.get("SWITCHCRAFT_SHADER_BUILD_DIR", ROOT / "build/shader-libraries"))
CORE_JAR = ROOT / ".deps/lwjgl_core.jar"
STB_JAR = ROOT / ".deps/lwjgl_stb.jar"
SHADERC_JAR = ROOT / ".deps/lwjgl_shaderc.jar"
SPVC_JAR = ROOT / ".deps/lwjgl_spvc.jar"
JSPECIFY_JAR = ROOT / ".deps/jspecify.jar"
LOCK = json.loads((ROOT / "dependencies.lock.json").read_text())


def ensure_jar(name: str, path: Path) -> None:
    pin = LOCK[name]
    if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == pin["sha256"]:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    urllib.request.urlretrieve(pin["url"], partial)
    if hashlib.sha256(partial.read_bytes()).hexdigest() != pin["sha256"]:
        partial.unlink(missing_ok=True)
        raise AssertionError(f"downloaded {name} JAR does not match dependencies.lock.json")
    partial.replace(path)


def ensure_host_builds() -> None:
    if not (ROOT / "build/lwjgl-core/host/liblwjgl-core.a").is_file():
        subprocess.run(["python3", "scripts/build-lwjgl-core.py", "--host"],
                       cwd=ROOT, check=True, capture_output=True, text=True)
    if not (ROOT / "build/lwjgl-utilities/host/liblwjgl_stb.so").is_file():
        subprocess.run(["python3", "scripts/build-lwjgl-utilities.py", "--host"],
                       cwd=ROOT, check=True, capture_output=True, text=True)
    if not (ROOT / "build/switchcraft-lwjgl-horizon.jar").is_file():
        subprocess.run(["python3", "scripts/build-lwjgl-horizon.py"],
                       cwd=ROOT, check=True, capture_output=True, text=True)
    if not (SHADER_BUILD / "host/libswitchcraft-shader-libraries-provider.a").is_file():
        subprocess.run(["python3", "scripts/build-shader-libraries.py", "--host"],
                       cwd=ROOT, check=True, capture_output=True, text=True)


class JavaUtilitiesSmokeTests(unittest.TestCase):
    def test_real_lwjgl_utility_calls_through_horizon_adapter(self):
        for name, path in (("lwjgl_core", CORE_JAR), ("lwjgl_stb", STB_JAR),
                           ("lwjgl_shaderc", SHADERC_JAR), ("lwjgl_spvc", SPVC_JAR)):
            ensure_jar(name, path)
        ensure_host_builds()
        if not (JAVA_SWITCH_SOURCE / "src/native_resolver.c").is_file():
            subprocess.run(["python3", "scripts/bootstrap-deps.py"], cwd=ROOT,
                           check=True, capture_output=True, text=True)
        required = (
            JAVA_SWITCH_SOURCE / "src/native_resolver.c", RUNTIME / "include/jni.h",
            CORE_JAR, STB_JAR, SHADERC_JAR, SPVC_JAR, JSPECIFY_JAR,
            ROOT / "build/switchcraft-lwjgl-horizon.jar",
            ROOT / "build/lwjgl-core/host/liblwjgl-core.a",
            ROOT / "build/lwjgl-core/host/libffi-private/.libs/libffi.a",
            ROOT / "build/lwjgl-utilities/host/liblwjgl_stb.so",
            SHADER_BUILD / "host/libswitchcraft-shader-libraries-provider.a",
        )
        for path in required:
            self.assertTrue(path.is_file(), f"required pinned build input is missing: {path}")
        source_revision = subprocess.check_output(
            ["git", "-C", str(JAVA_SWITCH_SOURCE), "rev-parse", "HEAD"], text=True).strip()
        self.assertEqual(source_revision, LOCK["java_switch"]["revision"],
                         "JAVA_SWITCH_SOURCE does not match the pinned resolver source")
        for key, path in (("lwjgl_core", CORE_JAR), ("lwjgl_stb", STB_JAR),
                          ("lwjgl_shaderc", SHADERC_JAR), ("lwjgl_spvc", SPVC_JAR)):
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), LOCK[key]["sha256"],
                             f"{key} JAR pin mismatch")

        with tempfile.TemporaryDirectory(prefix="java-utilities-") as temporary:
            work = Path(temporary)
            fixture_source = work / "utilities_native_fixture.c"
            fixture_source.write_text(r'''#include <jni.h>
#include <javaswitch/native_resolver.h>
#include <switchcraft/lwjgl_core.h>
#include <switchcraft/native_symbols_jni.h>
#include <switchcraft/shader_libraries.h>
#include <stdint.h>

extern jint JNI_OnLoad_lwjgl(JavaVM *, void *);
static int module_available(const char *module, void *context) {
    (void)context;
    return sc_lwjgl_core_available(module) || sc_shader_libraries_available(module);
}
static uintptr_t resolve_symbol(const char *module, const char *name, void *context) {
    (void)context;
    uintptr_t address = sc_lwjgl_core_lookup(module, name);
    return address != 0 ? address : sc_shader_libraries_lookup(module, name);
}
JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM *vm, void *reserved) {
    JNIEnv *env = NULL;
    if (JNI_OnLoad_lwjgl(vm, reserved) != JNI_VERSION_1_8 ||
        (*vm)->GetEnv(vm, (void **)&env, JNI_VERSION_1_8) != JNI_OK) return JNI_ERR;
    JsNativeResolver resolver = {
        JS_NATIVE_RESOLVER_ABI_VERSION, sizeof(resolver),
        module_available, resolve_symbol, NULL
    };
    if (js_native_resolver_install(&resolver) != JS_OK ||
        sc_register_native_symbols(vm, env, NULL) != 0) return JNI_ERR;
    return JNI_VERSION_1_8;
}
''')

            fixture = work / "libnative_fixture.so"
            host_jni = JDK.parent / "include"
            host_build = SHADER_BUILD / "host"
            spvc_archives = [host_build / "spirv-cross" / name for name in (
                "libspirv-cross-c.a", "libspirv-cross-core.a", "libspirv-cross-glsl.a",
                "libspirv-cross-hlsl.a", "libspirv-cross-msl.a", "libspirv-cross-cpp.a",
                "libspirv-cross-reflect.a")]
            for archive in spvc_archives:
                self.assertTrue(archive.is_file(), f"missing SPIRV-Cross archive: {archive}")
            core_archive = ROOT / "build/lwjgl-core/host/liblwjgl-core.a"
            private_ffi = ROOT / "build/lwjgl-core/host/libffi-private/.libs/libffi.a"
            cc = os.environ.get("CC", "cc")
            native_build = subprocess.run([
                cc, "-shared", "-fPIC", "-std=c11", "-Wall", "-Wextra", "-Werror",
                "-I", str(ROOT / "include"), "-I", str(SDK / "include"),
                "-I", str(host_jni), "-I", str(host_jni / "linux"),
                "-I", str(JAVA_SWITCH_SOURCE / "include"),
                str(fixture_source), str(ROOT / "src/native_symbols_jni.c"),
                str(JAVA_SWITCH_SOURCE / "src/native_resolver.c"),
                "-Wl,--whole-archive", str(core_archive),
                str(host_build / "libswitchcraft-shader-libraries-provider.a"),
                "-Wl,--no-whole-archive", "-Wl,--exclude-libs,libffi.a", str(private_ffi),
                str(host_build / "shaderc/libshaderc/libshaderc_combined.a"),
                "-Wl,--start-group", *(str(p) for p in spvc_archives), "-Wl,--end-group",
                "-lstdc++", "-lm", "-ldl", "-pthread", "-Wl,-z,notext",
                "-Wl,--no-undefined", "-o", str(fixture)
            ], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(native_build.returncode, 0, native_build.stdout + native_build.stderr)

            runner = work / "HostUtilitiesRunner.java"
            runner.write_text('''public final class HostUtilitiesRunner {
    public static void main(String[] args) throws Throwable {
        java.lang.foreign.Linker.nativeLinker(); // Initialize the genuine Linux FFM linker first.
        String hostOS = System.getProperty("os.name");
        if (!hostOS.toLowerCase().contains("linux"))
            throw new IllegalStateException("Host ABI check requires Linux, got " + hostOS);
        System.out.println("HOST_FFM_BOOTED os.arch=" + System.getProperty("os.arch"));
        System.setProperty("os.name", "Horizon"); // Select Switchcraft's adapter, retaining host ABI.
        System.load(args[0]); // Installs NativeSymbols and the upstream LWJGL core JNI bridge.
        org.switchcraft.runtime.HorizonUtilitiesSmoke.main(new String[0]);
    }
}
''')
            jars = [ROOT / "build/switchcraft-lwjgl-horizon.jar", CORE_JAR, STB_JAR,
                    SHADERC_JAR, SPVC_JAR, JSPECIFY_JAR]
            classpath = os.pathsep.join(map(str, [work, *jars]))
            subprocess.run([
                str(JDK / "javac"), "--release", "25", "-cp", classpath, "-d", str(work),
                str(ROOT / "java/org/switchcraft/runtime/HorizonUtilitiesSmoke.java"),
                str(runner),
            ], cwd=ROOT, check=True, capture_output=True, text=True)

            stb_native = ROOT / "build/lwjgl-utilities/host"
            env = os.environ.copy()
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                [str(stb_native), env.get("LD_LIBRARY_PATH", "")]).rstrip(os.pathsep)
            command = [
                str(JDK / "java"), "--enable-native-access=ALL-UNNAMED",
                "-Dorg.lwjgl.util.NoHashChecks=true", "-Dorg.lwjgl.libname=native_fixture",
                f"-Djava.library.path={os.pathsep.join((str(work), str(stb_native)))}",
                "-cp", classpath,
                "HostUtilitiesRunner", str(fixture),
            ]
            result = subprocess.run(command, cwd=ROOT, env=env, text=True,
                                    capture_output=True, timeout=120)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            for marker in ("HOST_FFM_BOOTED os.arch=", "SWITCHCRAFT_STB_PNG_JAVA_PASS",
                           "SWITCHCRAFT_SHADERC_JAVA_PASS", "SWITCHCRAFT_SPVC_REFLECTION_JAVA_PASS",
                           "SWITCHCRAFT_UTILITIES_JAVA_PASS"):
                self.assertIn(marker, output)
            for line in output.splitlines():
                if line.startswith(("HOST_FFM_BOOTED", "SWITCHCRAFT_")):
                    print(line)


if __name__ == "__main__":
    unittest.main()
