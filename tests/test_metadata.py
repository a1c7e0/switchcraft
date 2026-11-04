import hashlib
import json
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, relative, value):
        path = self.root/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))

    def version(self, name, **fields):
        self.write(f"versions/{name}/{name}.json", {"id": name, **fields})

    def inspect(self, name, success=True):
        result = subprocess.run([str(ROOT/"build/switchcraft-inspect"), str(self.root), name], capture_output=True, text=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        return result.stderr

    def test_inheritance_library_override_and_parent_jar(self):
        self.version("base", mainClass="example.Main", libraries=[{"name":"org.example:demo:1"}], javaVersion={"majorVersion":17},
                     arguments={"game":["--gameDir","${game_directory}"],"jvm":["-Dbase=true"]})
        self.version("fabric", inheritsFrom="base", libraries=[{"name":"org.example:demo:2"}], arguments={"game":["--fabric"]})
        plan=self.inspect("fabric")
        self.assertEqual(plan["java_major"],17)
        self.assertEqual(plan["main_class"],"example.Main")
        self.assertTrue(plan["classpath"][-1].endswith("base/base.jar"))
        self.assertIn("demo-2.jar",plan["classpath"][0])
        self.assertEqual(plan["game_arguments"][-1],"--fabric")
        self.assertIn("/instances/test/fabric",plan["game_arguments"][1])
        self.assertFalse(plan["launchable"])

    def test_rules_and_native_substitutions(self):
        self.version("v",mainClass="Main",libraries=[
            {"name":"test:linux:1","rules":[{"action":"allow","os":{"name":"linux"}}]},
            {"name":"test:shared:1","rules":[{"action":"allow"},{"action":"disallow","os":{"name":"windows"}}]},
            {"name":"org.lwjgl:lwjgl:2.9.4","natives":{"linux":"natives-linux"}},
            {"name":"org.lwjgl:lwjgl:3.3.3:natives-windows"}],
            arguments={"game":[{"rules":[{"action":"allow","features":{"is_demo_user":True}}],"value":"--demo"},"${auth_access_token}"]})
        p=self.inspect("v")
        self.assertEqual(p["skipped_libraries"],["test:linux:1"])
        self.assertEqual(len(p["native_substitutions"]),2)
        self.assertNotIn("--demo",p["game_arguments"])
        self.assertEqual(p["unresolved_placeholders"],["${auth_access_token}"])
        self.assertFalse(any("natives-windows" in x for x in p["classpath"]))

    def test_legacy_quotes_and_asset_index(self):
        self.version("legacy",mainClass="Main",assetIndex={"id":"1.12"},minecraftArguments='--name "two words" --assetsDir ${assets_root}')
        self.write("assets/indexes/1.12.json",{"objects":{"test":{"hash":"0"*40,"size":1}}})
        p=self.inspect("legacy")
        self.assertEqual(p["game_arguments"][1],"two words")
        self.assertEqual(p["asset_objects_declared"],1)
        self.assertEqual(p["java_major"],8)

    def test_cycle_missing_parent_traversal_and_bad_json(self):
        self.version("a",inheritsFrom="b");self.version("b",inheritsFrom="a")
        self.assertIn("cycle",self.inspect("a",False))
        self.version("missing",inheritsFrom="absent")
        self.assertIn("Cannot read",self.inspect("missing",False))
        self.assertIn("Invalid version",self.inspect("../outside",False))
        self.version("bad",libraries=[{"name":"a:b:1","downloads":{"artifact":{"path":"../../saves/file.jar"}}}])
        self.assertIn("Unsafe library",self.inspect("bad",False))
        self.write("versions/broken/broken.json",[])
        self.assertIn("Expected JSON object",self.inspect("broken",False))

    def test_read_only_and_no_token_substitution(self):
        self.version("v",mainClass="Main",minecraftArguments="--accessToken ${auth_access_token}")
        save=self.root/"saves/world/level.dat";save.parent.mkdir(parents=True);save.write_bytes(b"user save")
        before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}
        p=self.inspect("v")
        after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before,after)
        self.assertEqual(p["game_arguments"][-1],"${auth_access_token}")

    def test_official_manifest_listing(self):
        self.write("manifest.json",{"versions":[{"id":"1.20.1"},{"id":"../bad"},{"id":"26.4-snapshot"}]})
        p=subprocess.run([str(ROOT/"build/switchcraft-inspect"),"--manifest",str(self.root/"manifest.json")],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(p.stdout.splitlines(),["1.20.1","26.4-snapshot"])

    def test_snapshot_horizon_overrides_precede_lwjgl_and_options_are_explicit(self):
        self.version('26.4-snapshot-6',mainClass='net.minecraft.client.main.Main',
                     javaVersion={'majorVersion':25},libraries=[{'name':'org.lwjgl:lwjgl:3.4.3'}])
        plan=self.inspect('26.4-snapshot-6')
        self.assertTrue(plan['classpath'][0].endswith('/launchers/switchcraft-lwjgl-horizon.jar'))
        self.assertIn('lwjgl-3.4.3.jar',plan['classpath'][1])
        self.assertIn('--enable-native-access=ALL-UNNAMED',plan['jvm_arguments'])
        self.assertIn('--add-exports=java.base/jdk.internal.misc=ALL-UNNAMED',plan['jvm_arguments'])
        self.assertFalse(plan['launchable'])

    def test_prism_legacy_arguments_keep_strict_vulkan_and_maven_artifact_paths(self):
        self.version('26.4-snapshot-6',mainClass='net.minecraft.client.main.Main',
                     javaVersion={'majorVersion':25},
                     libraries=[{'name':'org.example:demo:1','downloads':{'artifact':{'url':'https://example.invalid/demo.jar'}}}],
                     minecraftArguments='--gameDir ${game_directory}')
        plan=self.inspect('26.4-snapshot-6')
        self.assertEqual(plan['game_arguments'][-2:],['--graphicsBackend','VULKAN'])
        self.assertIn('org/example/demo/1/demo-1.jar',plan['classpath'][1])
