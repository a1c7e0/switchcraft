from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
class CanvasTests(unittest.TestCase):
    def test_clipping_preserves_guards_and_touch_matches_visible_controls(self):
        with tempfile.TemporaryDirectory() as d:
            binary=Path(d)/'canvas'
            subprocess.run(['g++','-std=c++17','-O1','-Wall','-Wextra','-Werror','-Ivendor','-Isrc',
                'tests/ui_canvas_host.cpp','src/ui_canvas.cpp','src/launcher_ui.cpp','-o',str(binary)],cwd=ROOT,check=True)
            subprocess.run([str(binary)],check=True,timeout=10)
