import unittest
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


class WorkflowTests(unittest.TestCase):
 def test_launcher_controller_sequences(self):
     with tempfile.TemporaryDirectory() as tmp:
         binary = pathlib.Path(tmp) / "launcher-controller-host"
         subprocess.run([
             "g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
             "-Ivendor", "-Isrc", "tests/launcher_controller_host.cpp",
             "src/launcher_controller.cpp", "src/launcher_ui.cpp", "src/ui_canvas.cpp",
             "-o", str(binary),
         ], cwd=ROOT, check=True)
         subprocess.run([str(binary)], cwd=ROOT, check=True)

if __name__ == "__main__":
    unittest.main()
