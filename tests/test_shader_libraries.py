"""Exercise real shaderc compilation and SPIRV-Cross reflection APIs."""
import os
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILD = pathlib.Path(os.environ.get("SWITCHCRAFT_SHADER_BUILD_DIR", ROOT / "build/shader-libraries")) / "host"


class TestShaderLibraries(unittest.TestCase):
    def test_pinned_lwjgl_shader_functions_compile_and_reflect(self):
        subprocess.run(["python3", str(ROOT / "scripts/build-shader-libraries.py"), "--host"],
                       cwd=ROOT, check=True)
        smoke = BUILD / "shader_libraries_smoke"
        self.assertTrue(smoke.is_file(), "builder must create the real C API integration probe")
        subprocess.run([str(smoke)], cwd=ROOT, check=True)
        nm = subprocess.check_output(["nm", "-g", "--defined-only",
                                     str(BUILD / "shader_libraries_resolver.o")], text=True)
        self.assertIn("sc_shader_libraries_available", nm)
        self.assertIn("sc_shader_libraries_lookup", nm)


if __name__ == "__main__":
    unittest.main()
