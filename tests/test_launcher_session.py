import unittest
import pathlib, subprocess, tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
class WorkflowTests(unittest.TestCase):
 def test_launcher_session_workflows(self):
   with tempfile.TemporaryDirectory() as td:
     binary=pathlib.Path(td)/'session-host'; fixture=pathlib.Path(td)/'fixture'
     subprocess.run(['g++','-std=c++17','-O1','-Wall','-Wextra','-Werror','-Ivendor','-Isrc','tests/launcher_session_host.cpp','src/launcher_session.cpp','src/launcher_controller.cpp','src/launcher_ui.cpp','src/ui_canvas.cpp','src/launcher_jobs.cpp','src/instances.cpp','src/install.cpp','src/download.cpp','src/prism_metadata.cpp','src/metadata.cpp','-lcurl','-lcrypto','-pthread','-o',str(binary)],cwd=ROOT,check=True,timeout=120)
     subprocess.run([str(binary),str(fixture)],cwd=ROOT,check=True,timeout=30)

if __name__ == "__main__":
    unittest.main()
