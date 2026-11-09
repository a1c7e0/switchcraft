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
            (log / 'launcher-task-report.json').write_text('{"result":{"ok":false,"status":"cancelled"}}')
            (log / 'secret.txt').write_text('not included')
            out = base / 'feedback.zip'
            result = feedback.collect(sd, out)
            self.assertEqual(len(result['files']), 3)
            with zipfile.ZipFile(out) as archive:
                self.assertNotIn('switch/mc-runtime/logs/secret.txt', archive.namelist())
                self.assertIn('switch/mc-runtime/logs/launcher-task-report.json', archive.namelist())
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

    def test_unique_attempts_survive_one_export_and_other_files_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);sd=base/'sd';logs=sd/'switch/mc-runtime/logs';logs.mkdir(parents=True)
            captures=['java25-vm-100-stdout.log','java25-vm-101-stderr.log',
                      'switchcraft-java25-vm-200-stdout.log','vulkan-present-result-300.json']
            for name in captures:(logs/name).write_text(name)
            for name in ['java25-vm-secret-stdout.log','accounts.json','user.log']:(logs/name).write_text('private')
            out=base/'out.zip';feedback.collect(sd,out)
            with zipfile.ZipFile(out) as archive:
                self.assertEqual(set(archive.namelist()),{'collection.json',*['switch/mc-runtime/logs/'+n for n in captures]})

    def test_only_bounded_java_crash_reports_are_included(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); sd = base / 'sd'; logs = sd / 'switch/mc-runtime/logs'
            logs.mkdir(parents=True)
            (sd / 'manifest.json').write_text('{"target":"test"}')
            standalone = sd / 'switch/java25-test'; standalone.mkdir(parents=True)
            combined = sd / 'switch/switchcraft-java25'; combined.mkdir(parents=True)
            (standalone / 'hs_err_pid143.log').write_text('JVM crash details')
            (combined / 'hs_err_pid145.log').write_text('combined JVM crash details')
            (standalone / 'hs_err_pid143.txt').write_text('wrong extension')
            (sd / 'switch/atmosphere-crash.log').write_text('system crash details')
            out = base / 'feedback.zip'; result = feedback.collect(sd, out)
            expected = {'switch/java25-test/hs_err_pid143.log',
                        'switch/switchcraft-java25/hs_err_pid145.log'}
            with zipfile.ZipFile(out) as archive:
                names = set(archive.namelist())
                self.assertTrue(expected <= names)
                self.assertNotIn('switch/java25-test/hs_err_pid143.txt', names)
                self.assertNotIn('switch/atmosphere-crash.log', names)
                metadata = json.loads(archive.read('collection.json'))
                self.assertIn('Atmosphere/system crash dumps are not collected', metadata['crash_reports'])
            self.assertEqual(len(result['files']), 3)  # manifest plus two reports

    def test_crash_report_file_limit_is_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); sd = base / 'sd'; logs = sd / 'switch/mc-runtime/logs'
            logs.mkdir(parents=True)
            crash_dir = sd / 'switch/java25-test'; crash_dir.mkdir(parents=True)
            for pid in range(feedback.MAX_CRASH_REPORTS + 1):
                (crash_dir / f'hs_err_pid{pid}.log').write_text('x')
            with self.assertRaisesRegex(ValueError, 'more than 32'):
                feedback.collect(sd, base / 'out.zip')
            self.assertFalse((base / 'out.zip').exists())

    def test_total_export_size_is_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); sd = base / 'sd'; logs = sd / 'switch/mc-runtime/logs'
            logs.mkdir(parents=True)
            (sd / 'manifest.json').write_text('{"target":"test"}')
            out = base / 'out.zip'
            saved_limit = feedback.MAX_TOTAL_BYTES
            try:
                feedback.MAX_TOTAL_BYTES = 1
                with self.assertRaisesRegex(ValueError, '64 MiB total'):
                    feedback.collect(sd, out)
            finally:
                feedback.MAX_TOTAL_BYTES = saved_limit
            self.assertFalse(out.exists())
