import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
FIX=ROOT/'tests/fixtures/prism'
REAL=FIX/'real'

class PrismMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpbuild=tempfile.TemporaryDirectory()
        cls.bin=pathlib.Path(cls.tmpbuild.name)/'prism-host'
        subprocess.run(['g++','-std=c++17','-O0','-I'+str(ROOT/'vendor'),'-I'+str(ROOT/'src'),
            str(ROOT/'src/metadata.cpp'),str(ROOT/'src/prism_metadata.cpp'),str(ROOT/'tests/prism_metadata_host.cpp'),'-o',str(cls.bin)],check=True)
    @classmethod
    def tearDownClass(cls): cls.tmpbuild.cleanup()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=pathlib.Path(self.tmp.name)
        (self.root/'instances/demo/patches').mkdir(parents=True)
        (self.root/'meta/net.minecraft').mkdir(parents=True)
        (self.root/'meta/org.lwjgl3').mkdir(parents=True)
        shutil.copy(FIX/'mmc-pack.json',self.root/'instances/demo/mmc-pack.json')
        shutil.copy(FIX/'minecraft.json',self.root/'meta/net.minecraft/1.20.1.json')
        shutil.copy(FIX/'lwjgl.json',self.root/'meta/org.lwjgl3/3.3.2.json')
    def tearDown(self): self.tmp.cleanup()
    def run_resolve(self,ok=True):
        p=subprocess.run([str(self.bin),str(self.root),str(self.root/'instances/demo'),'x'],text=True,capture_output=True)
        if ok:self.assertEqual(p.returncode,0,p.stderr); return json.loads(p.stdout)
        self.assertNotEqual(p.returncode,0); return p.stderr
    def test_order_dependencies_library_override_and_java_args(self):
        j=self.run_resolve()
        self.assertEqual(j['_prism_component_order'],['net.minecraft','org.lwjgl3'])
        self.assertEqual([x['name'] for x in j['libraries']],['example:replace:2','example:base:1','example:lwjgl:3'])
        self.assertEqual(j['mainClass'],'net.minecraft.client.main.Main')
        self.assertEqual(j['assetIndex']['id'],'7')
        self.assertEqual(j['arguments']['jvm'],['-Dprism=true'])
    def test_dependency_missing_cycle_conflict_and_unknown_fail_closed(self):
        p=self.root/'meta/org.lwjgl3/3.3.2.json'
        obj=json.loads(p.read_text());obj['requires']=[{'uid':'absent'}];p.write_text(json.dumps(obj))
        self.assertIn('missing required',self.run_resolve(False))
        pack=self.root/'instances/demo/mmc-pack.json'; obj=json.loads(pack.read_text());obj['components'].append({'uid':'unknown.loader','version':'1'});pack.write_text(json.dumps(obj))
        self.assertIn('Unsupported Prism component UID',self.run_resolve(False))
    def test_local_patch_overrides_cached_metadata(self):
        patch={'uid':'org.lwjgl3','version':'3.3.2','requires':[{'uid':'net.minecraft','equals':'wrong'}],'libraries':[]}
        (self.root/'instances/demo/patches/org.lwjgl3.json').write_text(json.dumps(patch))
        self.assertIn('version mismatch',self.run_resolve(False))
    def test_requirement_cycle_conflict_and_unsupported_jarmod(self):
        p=self.root/'meta/org.lwjgl3/3.3.2.json'; obj=json.loads(p.read_text())
        obj['requires']=[{'uid':'net.minecraft','equals':'1.20.1'}]
        m=self.root/'meta/net.minecraft/1.20.1.json'; base=json.loads(m.read_text());base['requires']=[{'uid':'org.lwjgl3','equals':'3.3.2'}];m.write_text(json.dumps(base));p.write_text(json.dumps(obj))
        self.assertIn('dependency cycle',self.run_resolve(False))
        base.pop('requires');base['conflicts']=[{'uid':'org.lwjgl3'}];m.write_text(json.dumps(base))
        self.assertIn('conflict',self.run_resolve(False))
        base.pop('conflicts');base['jarMods']=[{'name':'untrusted.jar'}];m.write_text(json.dumps(base))
        self.assertIn('jarMods',self.run_resolve(False))
    def test_index_time_order(self):
        meta=self.root/'meta/org.example';meta.mkdir(parents=True)
        shutil.copy(FIX/'index.json',meta/'index.json')
        p=subprocess.run([str(self.bin),str(self.root),str(self.root/'instances/demo'),'index'],text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual([v['version'] for v in json.loads(p.stdout)],['new','old'])

    def test_real_snapshot_metadata_and_dependency_selection(self):
        # Real Prism cached JSON, pinned to snapshot-6 (the catalogue also has newer snapshot-7).
        shutil.copy(REAL/'net.minecraft.json',self.root/'meta/net.minecraft/26.4-snapshot-6.json')
        (self.root/'meta/org.lwjgl3').mkdir(parents=True,exist_ok=True)
        shutil.copy(REAL/'org.lwjgl3.json',self.root/'meta/org.lwjgl3/3.4.3.json')
        shutil.copy(REAL/'net.minecraft-index.json',self.root/'meta/net.minecraft/index.json')
        p=subprocess.run([str(self.bin),str(self.root),'26.4-snapshot-6','components'],text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout),[{'uid':'net.minecraft','version':'26.4-snapshot-6'},{'uid':'org.lwjgl3','version':'3.4.3'}])
        pack=self.root/'instances/demo/mmc-pack.json';pack.write_text(json.dumps({'formatVersion':1,'components':json.loads(p.stdout)}))
        j=self.run_resolve()
        self.assertEqual(j['javaVersion']['majorVersion'],25)
        self.assertEqual(j['_main_jar_path'],'libraries/com/mojang/minecraft/26.4-snapshot-6/minecraft-26.4-snapshot-6-client.jar')
        self.assertIn('XR:Initial',j['traits'])
        self.assertEqual(j['minecraftArguments'].split()[:2],['--username','${auth_player_name}'])
        self.assertIn('-XX:StackShadowPages=32',j['arguments']['jvm'])
        self.assertEqual(j['id'],'26.4-snapshot-6')
    def test_index_sorts_offsets_as_instants_and_rejects_invalid_date(self):
        meta=self.root/'meta/org.example';meta.mkdir(parents=True)
        idx={'formatVersion':1,'uid':'org.example','versions':[
            {'version':'later','releaseTime':'2026-01-01T01:00:00+01:00','type':'snapshot'},
            {'version':'earlier','releaseTime':'2026-01-01T00:30:00Z','type':'snapshot'}]}
        (meta/'index.json').write_text(json.dumps(idx))
        p=subprocess.run([str(self.bin),str(self.root),str(self.root/'instances/demo'),'index'],text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual([v['version'] for v in json.loads(p.stdout)],['earlier','later'])
        idx['versions'][0]['releaseTime']='2026-02-30T01:00:00+01:00'
        (meta/'index.json').write_text(json.dumps(idx))
        p=subprocess.run([str(self.bin),str(self.root),str(self.root/'instances/demo'),'index'],text=True,capture_output=True)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('Invalid Prism releaseTime fields',p.stderr)
