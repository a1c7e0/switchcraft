"""Compile and optionally execute the Java 25 SDL3/Vulkan/VMA smoke."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "dependencies.lock.json").read_text())
ARTIFACTS = {
    "core": "lwjgl_core",
    "core_native": "lwjgl_core_host_linux",
    "sdl": "lwjgl_sdl",
    "sdl_native": "lwjgl_sdl_host_linux",
    "vulkan": "lwjgl_vulkan",
    "vma": "lwjgl_vma",
    "vma_native": "lwjgl_vma_host_linux",
}
JAVA_ROOT = ROOT / ".deps/host-jdk25"


def host_java(tool):
    override = os.environ.get("HOST_JDK")
    if override:
        candidate = Path(override)
        if candidate.is_dir():
            candidate /= "bin"
        candidate /= tool
        return candidate
    candidates = sorted(JAVA_ROOT.glob(f"*/bin/{tool}"))
    return candidates[-1] if candidates else None


def locked_jar(key):
    entry = LOCK[key]
    path = ROOT / ".deps/java-graphics" / f"{key}.jar"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
        path.unlink()
    if not path.exists():
        partial = path.with_suffix(".partial")
        try:
            urllib.request.urlretrieve(entry["url"], partial)
            if hashlib.sha256(partial.read_bytes()).hexdigest() != entry["sha256"]:
                raise AssertionError(f"SHA-256 mismatch for locked artifact {key}")
            partial.replace(path)
        finally:
            partial.unlink(missing_ok=True)
    if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
        raise AssertionError(f"SHA-256 mismatch for locked artifact {key}")
    return path


class JavaGraphicsSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        javac, java = host_java("javac"), host_java("java")
        if not javac or not java or not javac.is_file() or not java.is_file():
            raise unittest.SkipTest("Java 25 host JDK is unavailable")
        cls.java = java
        cls.jars = {key: locked_jar(lock_key) for key, lock_key in ARTIFACTS.items()}
        cls.temp = tempfile.TemporaryDirectory(prefix="switchcraft-java-graphics-")
        cls.classes = Path(cls.temp.name) / "classes"
        cls.classes.mkdir()
        compile_cp = os.pathsep.join(str(cls.jars[k]) for k in ("core", "sdl", "vulkan", "vma"))
        source = ROOT / "java/org/switchcraft/runtime/HorizonGraphicsSmoke.java"
        subprocess.run([str(javac), "--release", "25", "-cp", compile_cp, "-d", str(cls.classes), str(source)], check=True)

    @classmethod
    def tearDownClass(cls):
        temp = getattr(cls, "temp", None)
        if temp:
            temp.cleanup()

    def test_compiles_against_locked_lwjgl_343_apis(self):
        self.assertTrue((self.classes / "org/switchcraft/runtime/HorizonGraphicsSmoke.class").is_file())

    @unittest.skipUnless(os.environ.get("SWITCHCRAFT_GRAPHICS_HOST_RUN") == "1",
                         "Set SWITCHCRAFT_GRAPHICS_HOST_RUN=1 with a host display and Vulkan ICD")
    def test_host_sdl_vulkan_and_vma_present_60_frames(self):
        if not os.environ.get("DISPLAY"):
            self.fail("SWITCHCRAFT_GRAPHICS_HOST_RUN=1 requires DISPLAY")
        classpath = [str(self.classes)] + [str(self.jars[k]) for k in ARTIFACTS]
        completed = subprocess.run(
            [str(self.java), "--enable-native-access=ALL-UNNAMED", "-cp", os.pathsep.join(classpath),
             "org.switchcraft.runtime.HorizonGraphicsSmoke"],
            env=os.environ.copy(), capture_output=True, text=True, timeout=120,
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, f"Host graphics smoke failed; no pass claimed:\n{output}")
        self.assertIn("VMA allocator initialized", output)
        self.assertIn("VMA allocator destroyed", output)
        self.assertIn("PRESENTATION_PASS frames=60", output)


if __name__ == "__main__":
    unittest.main()
