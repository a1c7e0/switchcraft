import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('feedback', ROOT / 'tools/collect-feedback.py')
feedback = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feedback)

class FeedbackTests(unittest.TestCase):
    def test_allowlist_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); sd = base / 'sd'; log = sd / 'switch/mc-runtime/logs'
            log.mkdir(parents=True)
            (sd / 'manifest.json').write_text('{"target":"test"}')
            (log / 'vulkan-present.log').write_text('stage: surface')
            (log / 'secret.txt').write_text('not included')
            out = base / 'feedback.zip'
            result = feedback.collect(sd, out)
            self.assertEqual(len(result['files']), 2)
            with zipfile.ZipFile(out) as archive:
                self.assertNotIn('switch/mc-runtime/logs/secret.txt', archive.namelist())
                self.assertEqual(json.loads(archive.read('collection.json'))['hardware_status'], 'NOT VERIFIED by collection')
            with self.assertRaises(FileExistsError): feedback.collect(sd, out)
            with self.assertRaises(ValueError): feedback.collect(sd, sd / 'bad.zip')

    def test_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); sd = base / 'sd'; logs = sd / 'switch/mc-runtime/logs'
            logs.mkdir(parents=True); outside = base / 'outside'; outside.write_text('private')
            (logs / 'ffi-test.log').symlink_to(outside)
            with self.assertRaises(ValueError): feedback.collect(sd, base / 'out.zip')
            self.assertFalse((base / 'out.zip').exists())
