from pathlib import Path
import subprocess,tempfile,unittest,json
ROOT=Path(__file__).resolve().parents[1]
class ConfigTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.exe=Path(cls.tmp.name)/'config'
  subprocess.run(['g++','-std=c++17','-O1','-Ivendor','-Isrc','tests/config_host.cpp','src/metadata.cpp','-o',str(cls.exe)],cwd=ROOT,check=True)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_preferences_preserve_unknown_settings_and_do_not_follow_stale_stage(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'launcher.json';other=root/'save';other.write_bytes(b'untouched')
   p.write_text(json.dumps({'minecraft_root':str(root/'game'),'network_ca_file':'custom.pem','extra':{'value':1}}))
   (root/'launcher.json.tmp').symlink_to(other)
   subprocess.run([str(self.exe),str(p)],check=True)
   j=json.loads(p.read_text());self.assertEqual(j['heap_mib'],512);self.assertEqual(j['network_ca_file'],'custom.pem');self.assertEqual(j['extra'],{'value':1});self.assertEqual(other.read_bytes(),b'untouched')
 def test_malformed_config_and_symlink_destination_are_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'launcher.json';p.write_text('{bad')
   self.assertNotEqual(subprocess.run([str(self.exe),str(p)],capture_output=True).returncode,0);self.assertEqual(p.read_text(),'{bad')
   p.unlink();other=root/'original';raw='{"heap_mib":256}';other.write_text(raw);p.symlink_to(other)
   self.assertNotEqual(subprocess.run([str(self.exe),str(p)],capture_output=True).returncode,0);self.assertEqual(other.read_text(),raw)
