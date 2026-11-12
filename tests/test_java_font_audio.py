#!/usr/bin/env python3
"""Exercise pinned LWJGL FreeType/OpenAL through Horizon's real FFM adapter."""
from __future__ import annotations

import glob
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
JDK = next((ROOT / ".deps/host-jdk25").glob("*/bin"))
SDK = ROOT / "build/java25-integrated/sdk"
RUNTIME = ROOT / "build/java25-integrated/runtime/openjdk25-horizon-runtime"
JAVA_SWITCH_SOURCE = Path(os.environ.get("JAVA_SWITCH_SOURCE", ROOT / ".deps/java-switch"))
CORE_JAR = ROOT / ".deps/lwjgl_core.jar"
FREETYPE_JAR = ROOT / ".deps/lwjgl_freetype.jar"
OPENAL_JAR = ROOT / ".deps/lwjgl_openal.jar"
JSPECIFY_JAR = ROOT / ".deps/jspecify.jar"
LOCK = json.loads((ROOT / "dependencies.lock.json").read_text())


class JavaFontAudioTests(unittest.TestCase):
    def test_public_lwjgl_font_audio_calls_use_horizon_ffm_and_jni_bridge(self):
        for path in (JAVA_SWITCH_SOURCE / "src/native_resolver.c",
                     RUNTIME / "include/jni.h", CORE_JAR, FREETYPE_JAR,
                     OPENAL_JAR, JSPECIFY_JAR):
            self.assertTrue(path.is_file(), f"required pinned build input is missing: {path}")
        source_revision = subprocess.check_output(
            ["git", "-C", str(JAVA_SWITCH_SOURCE), "rev-parse", "HEAD"], text=True).strip()
        self.assertEqual(source_revision, LOCK["java_switch"]["revision"],
                         "JAVA_SWITCH_SOURCE does not match the pinned resolver source")
        for key, path in (("lwjgl_core", CORE_JAR),
                          ("lwjgl_freetype", FREETYPE_JAR),
                          ("lwjgl_openal", OPENAL_JAR)):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, LOCK[key]["sha256"], f"{key} JAR pin mismatch")

        if not (ROOT / "build/lwjgl-core/host/liblwjgl-core.a").is_file():
            subprocess.run(["python3", "scripts/build-lwjgl-core.py", "--host"],
                           cwd=ROOT, check=True, capture_output=True, text=True)
        if not (ROOT / "build/font-audio/host/libswitchcraft-font-audio.so").is_file():
            subprocess.run(["python3", "scripts/build-font-audio.py", "--host"],
                           cwd=ROOT, check=True, capture_output=True, text=True)
        if not (ROOT / "build/switchcraft-lwjgl-horizon.jar").is_file():
            subprocess.run(["python3", "scripts/build-lwjgl-horizon.py"],
                           cwd=ROOT, check=True, capture_output=True, text=True)

        with tempfile.TemporaryDirectory(prefix="java-font-audio-") as temporary:
            work = Path(temporary)
            fixture_source = work / "font_audio_native_fixture.c"
            fixture_source.write_text(r'''#include <jni.h>
#include <javaswitch/native_resolver.h>
#include <switchcraft/font_audio.h>
#include <switchcraft/lwjgl_core.h>
#include <switchcraft/native_symbols_jni.h>
#include <stdint.h>

extern jint JNI_OnLoad_lwjgl(JavaVM *, void *);

static int module_available(const char *module, void *context) {
    (void)context;
    return sc_lwjgl_core_available(module) || sc_font_audio_available(module);
}

static uintptr_t resolve_symbol(const char *module, const char *name, void *context) {
    (void)context;
    uintptr_t address = sc_lwjgl_core_lookup(module, name);
    return address != 0 ? address : sc_font_audio_lookup(module, name);
}

JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM *vm, void *reserved) {
    JNIEnv *env = NULL;
    if (JNI_OnLoad_lwjgl(vm, reserved) != JNI_VERSION_1_8 ||
        (*vm)->GetEnv(vm, (void **)&env, JNI_VERSION_1_8) != JNI_OK) {
        return JNI_ERR;
    }
    JsNativeResolver resolver = {
        JS_NATIVE_RESOLVER_ABI_VERSION, sizeof(resolver),
        module_available, resolve_symbol, NULL
    };
    if (js_native_resolver_install(&resolver) != JS_OK ||
        sc_register_native_symbols(vm, env, NULL) != 0) {
        return JNI_ERR;
    }
    return JNI_VERSION_1_8;
}
''')

            fixture = work / "libnative_fixture.so"
            host_jni = JDK.parent / "include"
            audio_provider = ROOT / "build/font-audio/host/libswitchcraft-font-audio.so"
            core_archive = ROOT / "build/lwjgl-core/host/liblwjgl-core.a"
            libffi_archive = ROOT / "build/lwjgl-core/host/libffi-private/.libs/libffi.a"
            self.assertTrue(libffi_archive.is_file(), "private pinned host libffi archive is missing")
            native_build = subprocess.run([
                "cc", "-shared", "-fPIC", "-std=c11", "-Wall", "-Wextra", "-Werror",
                "-I", str(ROOT / "include"), "-I", str(SDK / "include"),
                "-I", str(host_jni), "-I", str(host_jni / "linux"),
                "-I", str(JAVA_SWITCH_SOURCE / "include"),
                str(fixture_source), str(ROOT / "src/native_symbols_jni.c"),
                str(JAVA_SWITCH_SOURCE / "src/native_resolver.c"),
                "-Wl,--whole-archive", str(core_archive), "-Wl,--no-whole-archive",
                "-Wl,--exclude-libs,libffi.a", str(libffi_archive), "-ldl",
                "-L", str(audio_provider.parent),
                "-lswitchcraft-font-audio", f"-Wl,-rpath,{audio_provider.parent}",
                "-pthread", "-Wl,--no-undefined", "-o", str(fixture)
            ], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(native_build.returncode, 0, native_build.stdout + native_build.stderr)

            runner = work / "HostFontAudioRunner.java"
            runner.write_text('''public final class HostFontAudioRunner {
    public static void main(String[] args) throws Throwable {
        java.lang.foreign.Linker.nativeLinker(); // Boot Linux FFM before selecting the adapter.
        String hostOS = System.getProperty("os.name");
        if (!hostOS.toLowerCase().contains("linux")) {
            throw new IllegalStateException("This host ABI check requires Linux, got " + hostOS);
        }
        System.out.println("HOST_FFM_BOOTED os.arch=" + System.getProperty("os.arch"));
        System.setProperty("os.name", "Horizon"); // Select the adapter without changing host FFM/ABI.
        System.load(args[0]); // Registers NativeSymbols and upstream LWJGL core JNI.
        org.switchcraft.runtime.HorizonFontAudioSmoke.main(
            args.length > 1 ? new String[] { args[1] } : new String[0]);
    }
}
''')
            classpath_jars = [
                ROOT / "build/switchcraft-lwjgl-horizon.jar",
                CORE_JAR,
                FREETYPE_JAR,
                OPENAL_JAR,
                JSPECIFY_JAR,
            ]
            classpath = os.pathsep.join(map(str, [work, *classpath_jars]))
            subprocess.run([
                str(JDK / "javac"), "--release", "25", "-cp", classpath, "-d", str(work),
                str(ROOT / "java/org/switchcraft/runtime/NativeSymbols.java"),
                str(ROOT / "java/org/switchcraft/runtime/HorizonFontAudioSmoke.java"),
                str(runner),
            ], cwd=ROOT, check=True, capture_output=True, text=True)

            fonts = (glob.glob("/usr/share/fonts/**/*.ttf", recursive=True)
                     + glob.glob("/usr/share/fonts/**/*.otf", recursive=True))
            command = [
                str(JDK / "java"), "--enable-native-access=ALL-UNNAMED",
                "-Dorg.lwjgl.util.NoHashChecks=true", "-Dorg.lwjgl.libname=native_fixture",
                f"-Djava.library.path={work}", "-cp", classpath,
                "HostFontAudioRunner", str(fixture),
            ]
            if fonts:
                command.append(fonts[0])
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("HOST_FFM_BOOTED os.arch=", result.stdout)
            self.assertIn("SWITCHCRAFT_FREETYPE_JAVA_PASS version=", result.stdout)
            if fonts:
                self.assertIn("SWITCHCRAFT_FREETYPE_GLYPH_PASS codepoint=65", result.stdout)
            self.assertIn("SWITCHCRAFT_OPENAL_LOOPBACK_JAVA_PASS frames=4096 nonzero=", result.stdout)
            self.assertIn("SWITCHCRAFT_FONT_AUDIO_JAVA_PASS hardware_output=NOT_TESTED", result.stdout)
            for line in result.stdout.splitlines():
                if line.startswith(("HOST_FFM_BOOTED", "SWITCHCRAFT_")):
                    print(line)


if __name__ == "__main__":
    unittest.main()
