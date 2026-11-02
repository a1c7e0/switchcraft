import importlib.util
import pathlib
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("verify",ROOT/"scripts/verify-artifacts.py")
verify=importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)

class ArtifactTests(unittest.TestCase):
    def test_actual_binaries(self):
        for app in verify.APPS:
            self.assertEqual(verify.verify(ROOT/"dist"/(app+".nro"),ROOT/"build"/(app+".elf"))["build_verification"],"PASS")

    def test_renamed_elf_and_truncation_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            nro=pathlib.Path(d)/"switch-diagnostics.nro"
            elf=ROOT/"build/switch-diagnostics.elf"
            nro.write_bytes(elf.read_bytes())
            with self.assertRaises(AssertionError):verify.verify(nro,elf)
            nro.write_bytes((ROOT/"dist/switch-diagnostics.nro").read_bytes()[:4096])
            with self.assertRaises(AssertionError):verify.verify(nro,elf)
