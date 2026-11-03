import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('prepare_java25',ROOT/'scripts/prepare-java25-runtime.py')
prepare=importlib.util.module_from_spec(spec);spec.loader.exec_module(prepare)
class Java25PackageTests(unittest.TestCase):
    def test_mutated_runtime_or_sdk_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'integrated'
            shutil.copytree(ROOT/'build/java25-integrated',root)
            prepare.verify_unpacked(root)
            cfg=root/'runtime/openjdk25-horizon-runtime/runtime/conf/net.properties'
            original=cfg.read_bytes();cfg.write_bytes(original+b'\nchanged')
            with self.assertRaisesRegex(RuntimeError,'content mismatch'):
                prepare.verify_unpacked(root)
            cfg.write_bytes(original)
            header=root/'sdk/include/javaswitch/runtime.h';header.write_bytes(header.read_bytes()+b'\nchanged')
            with self.assertRaisesRegex(RuntimeError,'content mismatch'):
                prepare.verify_unpacked(root)
