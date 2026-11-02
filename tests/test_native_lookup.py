import pathlib
import subprocess
import tempfile
import unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
class NativeLookupTests(unittest.TestCase):
    def test_allowlisted_function_lookup_and_call(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / 'lookup-test'
            subprocess.run(['gcc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Iinclude',
                            'src/native_lookup.c', 'tests/native_lookup_host.c',
                            '-o', str(output)], cwd=ROOT, check=True)
            subprocess.run([str(output)], cwd=ROOT, check=True)
