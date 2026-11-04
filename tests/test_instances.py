import json
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class InstanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = tempfile.TemporaryDirectory()
        cls.binary = pathlib.Path(cls.build.name) / 'instances-host'
        result = subprocess.run([
            'c++', '-std=c++17', '-Wall', '-Wextra', '-Isrc', '-Ivendor',
            'tests/instances_host.cpp', 'src/instances.cpp', 'src/metadata.cpp', 'src/prism_metadata.cpp',
            '-o', str(cls.binary)
        ], cwd=ROOT, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.build.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.shared = self.root / 'shared'
        self.runtime = self.root / 'mc-runtime'
        (self.shared / 'versions' / '26.4-snapshot-6').mkdir(parents=True)
        (self.shared / 'versions' / '26.4-snapshot-6' / '26.4-snapshot-6.json').write_text(json.dumps({
            'id': '26.4-snapshot-6', 'mainClass': 'example.Main', 'javaVersion': {'majorVersion': 25},
            'arguments': {'game': ['--gameDir', '${game_directory}']}, 'libraries': []
        }))
        self.runtime.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, *args, ok=True):
        result = subprocess.run([str(self.binary), str(self.runtime), str(self.shared), *args], capture_output=True, text=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def test_prism_profile_crud_isolation_and_planner_path(self):
        created = self.call('create', 'Main Profile', '26.4-snapshot-6', '768')
        info = json.loads(created.stdout)
        inst = self.runtime / 'instances' / info['id']
        self.assertTrue((inst / 'instance.cfg').is_file())
        self.assertTrue((inst / 'mmc-pack.json').is_file())
        self.assertTrue((inst / '.minecraft').is_dir())
        cfg = (inst / 'instance.cfg').read_text()
        self.assertIn('InstanceType=OneSix', cfg)
        self.assertIn('MaxMemAlloc=768', cfg)
        pack = json.loads((inst / 'mmc-pack.json').read_text())
        self.assertEqual(pack['components'][0]['uid'], 'net.minecraft')
        planned = json.loads(self.call('plan', info['id']).stdout)
        self.assertEqual(planned['game_directory'], str(inst / '.minecraft'))
        self.assertIn(str(inst / '.minecraft'), planned['game_arguments'])
        self.call('rename', info['id'], 'Renamed')
        self.assertEqual(json.loads(self.call('list').stdout)[0]['name'], 'Renamed')
        self.call('set', info['id'], '26.4-snapshot-6', '512')
        self.assertIn('MaxMemAlloc=512', (inst / 'instance.cfg').read_text())

    def test_prism_ini_roundtrips_quoted_unicode_and_escaped_characters(self):
        label='World, 1; +# "雪"'
        info=json.loads(self.call('create',label,'26.4-snapshot-6','512').stdout)
        inst=self.runtime/'instances'/info['id']
        raw=(inst/'instance.cfg').read_text()
        self.assertIn('"World, 1; +\\# \\"雪\\""', raw)
        self.assertEqual(json.loads(self.call('list').stdout)[0]['name'],label)
        # Saving another setting must preserve other valid Prism scalar settings.
        with (inst/'instance.cfg').open('a') as f:
            f.write('[General]\nCustom=one\\#two\n')
        self.call('rename',info['id'],label)
        after=(inst/'instance.cfg').read_text()
        self.assertIn('[General]\nCustom=one\\#two',after)
        self.assertEqual(json.loads(self.call('list').stdout)[0]['name'],label)

    def test_duplicate_has_empty_game_directory_and_no_install_writes(self):
        info=json.loads(self.call('create','Original','26.4-snapshot-6','512').stdout)
        origin=self.runtime/'instances'/info['id']/'.minecraft'
        (origin/'saves'/'world').mkdir(parents=True)
        (origin/'saves'/'world'/'level.dat').write_bytes(b'save')
        (origin/'options.txt').write_text('video settings')
        source=self.runtime/'instances'/info['id']
        (source/'instance.cfg').write_text((source/'instance.cfg').read_text()+'[LauncherExtra]\nCustom=kept\\#value\n')
        pack_path=source/'mmc-pack.json'
        pack=json.loads(pack_path.read_text()); pack['customField']={'keep':True}; pack['components'].append({'uid':'org.lwjgl3','version':'3.4.3'})
        pack_path.write_text(json.dumps(pack))
        (source/'patches').mkdir()
        (source/'patches'/'net.minecraft.json').write_text(json.dumps({'uid':'net.minecraft','mainClass':'custom.Main'}))
        before={p.relative_to(self.shared):p.read_bytes() for p in self.shared.rglob('*') if p.is_file()}
        dup=json.loads(self.call('duplicate',info['id'],'Copy').stdout)
        target_root=self.runtime/'instances'/dup['id']
        target=target_root/'.minecraft'
        self.assertFalse((target/'saves').exists())
        self.assertFalse((target/'options.txt').exists())
        self.assertIn('Custom=kept\\#value',(target_root/'instance.cfg').read_text())
        cloned_pack=json.loads((target_root/'mmc-pack.json').read_text())
        self.assertEqual(cloned_pack['components'],pack['components'])
        self.assertEqual(cloned_pack['customField'],{'keep':True})
        self.assertEqual((target_root/'patches'/'net.minecraft.json').read_bytes(),(source/'patches'/'net.minecraft.json').read_bytes())
        after={p.relative_to(self.shared):p.read_bytes() for p in self.shared.rglob('*') if p.is_file()}
        self.assertEqual(before,after)

    def test_traversal_malformed_metadata_collision_and_heap_bounds(self):
        (self.runtime/'instances'/'java-smoke').mkdir(parents=True)
        self.call('create','Same Name','26.4-snapshot-6','512')
        self.call('create','Same Name','26.4-snapshot-6','512')
        listed=json.loads(self.call('list').stdout)
        self.assertEqual(len(listed),2)
        self.call('load','../outside',ok=False)
        self.call('create','Bad Heap','26.4-snapshot-6','2048',ok=False)
        broken=self.runtime/'instances'/'broken'
        broken.mkdir(); (broken/'.minecraft').mkdir(); (broken/'instance.cfg').write_text('not ini'); (broken/'mmc-pack.json').write_text('{')
        before=(broken/'instance.cfg').read_bytes()
        self.call('load','broken',ok=False)
        self.call('rename','broken','Do not clobber',ok=False)
        self.assertEqual((broken/'instance.cfg').read_bytes(),before)

    def test_prism_cached_version_is_resolved_without_download(self):
        meta=self.shared/'meta'/'net.minecraft'
        meta.mkdir(parents=True)
        (meta/'index.json').write_text(json.dumps({'formatVersion': 1, 'versions': [{'version':'snapshot-x','releaseTime':'2026-01-01T00:00:00Z'}]}))
        (meta/'snapshot-x.json').write_text(json.dumps({'uid':'net.minecraft','version':'snapshot-x','mainClass':'example.Snapshot','libraries':[], 'arguments':{}, 'javaVersion':{'majorVersion':25}, 'requires':[{'uid':'org.lwjgl3','suggests':'3.4.3'}]}))
        lwjgl=self.shared/'meta'/'org.lwjgl3'
        lwjgl.mkdir(parents=True)
        (lwjgl/'3.4.3.json').write_text(json.dumps({'uid':'org.lwjgl3','version':'3.4.3','libraries':[]}))
        info=json.loads(self.call('create','Cached','snapshot-x','512').stdout)
        pack=json.loads((self.runtime/'instances'/info['id']/'mmc-pack.json').read_text())
        self.assertEqual([c['uid'] for c in pack['components']],['net.minecraft','org.lwjgl3'])
        plan=json.loads(self.call('plan',info['id']).stdout)
        self.assertEqual(plan['main_class'],'example.Snapshot')
        self.assertEqual(plan['version'],'snapshot-x')
        self.assertFalse(plan['launchable'])

    def test_symlink_instance_and_metadata_are_rejected(self):
        out=self.root/'outside'; out.mkdir()
        (self.runtime/'instances').mkdir()
        (self.runtime/'instances'/'link').symlink_to(out, target_is_directory=True)
        self.call('load','link',ok=False)
        profile=self.runtime/'instances'/'metadata-link'
        profile.mkdir(); (profile/'.minecraft').mkdir()
        (profile/'instance.cfg').symlink_to(out/'instance.cfg')
        (profile/'mmc-pack.json').write_text('{}')
        self.call('load','metadata-link',ok=False)

if __name__ == '__main__':
    unittest.main()
