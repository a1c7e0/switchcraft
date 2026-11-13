"""Check diagnostic choices and bounded menu formatting without libnx."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class Java25MenuTests(unittest.TestCase):
    def test_menu_choices_revision_and_bounds(self):
        with tempfile.TemporaryDirectory() as directory:
            exe=Path(directory)/"menu"
            subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-Iinclude",
                "tests/java25_menu_host.c","-o",str(exe)],cwd=ROOT,check=True)
            subprocess.run([str(exe)],check=True)
