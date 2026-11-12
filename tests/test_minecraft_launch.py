import hashlib
import json
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION = "26.4-snapshot-6"
CLIENT_PATH = "com/mojang/minecraft/26.4-snapshot-6/minecraft-26.4-snapshot-6-client.jar"


class MinecraftLaunchRequestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.binary = pathlib.Path(cls.temp.name) / "minecraft-launch-host"
        subprocess.run([
            "g++", "-std=c++17", "-O0", "-Wall", "-Wextra", "-Werror",
            "-Iinclude", "-Ivendor", "-Isrc", "tests/minecraft_launch_host.cpp",
            "src/minecraft_launch_request.cpp", "src/instances.cpp", "src/install.cpp",
            "src/download.cpp", "src/prism_metadata.cpp", "src/metadata.cpp",
            "-lcurl", "-lcrypto", "-pthread", "-o", str(cls.binary),
        ], cwd=ROOT, check=True, timeout=120)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def fixture(self, base):
        runtime, shared = base / "runtime", base / "shared"
        (runtime / "config").mkdir(parents=True)
        (runtime / "tmp").mkdir()
        (runtime / "launchers").mkdir()
        (shared / "meta/net.minecraft").mkdir(parents=True)
        (shared / "assets/indexes").mkdir(parents=True)
        (shared / "libraries/com/mojang/minecraft/26.4-snapshot-6").mkdir(parents=True)
        (runtime / "launchers/switchcraft-lwjgl-horizon.jar").write_bytes(b"overlay")
        (runtime / "launchers/switchcraft-launcher-bridge.jar").write_bytes(b"agent")
        client = b"client fixture"
        (shared / "libraries" / CLIENT_PATH).write_bytes(client)
        asset_index = b'{"objects":{}}'
        (shared / "assets/indexes/36.json").write_bytes(asset_index)
        sha1 = lambda data: hashlib.sha1(data).hexdigest()
        metadata = {
            "uid": "net.minecraft", "version": VERSION,
            "mainClass": "net.minecraft.client.main.Main",
            "compatibleJavaMajors": [25],
            "arguments": {"jvm": [], "game": []},
            "mainJar": {
                "name": "com.mojang:minecraft:26.4-snapshot-6:client",
                "downloads": {"artifact": {
                    "path": CLIENT_PATH, "sha1": sha1(client), "size": len(client),
                    "url": "https://example.invalid/client.jar",
                }},
            },
            "assetIndex": {
                "id": "36", "sha1": sha1(asset_index), "size": len(asset_index),
                "url": "https://example.invalid/assets.json",
            },
            "libraries": [],
        }
        metadata_bytes = (json.dumps(metadata, separators=(",", ":")) + "\n").encode()
        (shared / f"meta/net.minecraft/{VERSION}.json").write_bytes(metadata_bytes)
        index = {
            "uid": "net.minecraft", "formatVersion": 1,
            "versions": [{"version": VERSION, "sha256": hashlib.sha256(metadata_bytes).hexdigest(),
                          "type": "snapshot", "releaseTime": "2026-10-27T13:40:29+00:00"}],
        }
        (shared / "meta/net.minecraft/index.json").write_text(json.dumps(index))
        (runtime / "config/launcher.json").write_text(json.dumps({
            "minecraft_root": str(shared), "runtime": "openjdk25", "graphics": "nvk", "heap_mib": 512,
        }))
        profile = runtime / "instances/demo"
        (profile / ".minecraft").mkdir(parents=True)
        (profile / "instance.cfg").write_text(
            "ConfigVersion=1.3\nname=Demo\nInstanceType=OneSix\nMaxMemAlloc=768\n")
        (profile / "mmc-pack.json").write_text(json.dumps({
            "formatVersion": 1,
            "components": [{"uid": "net.minecraft", "version": VERSION}],
        }))
        return runtime, shared, profile

    def call_host(self, op, runtime, shared):
        result = subprocess.run(
            [str(self.binary), op, str(runtime), str(shared), "demo"],
            cwd=ROOT, check=True, text=True, capture_output=True, timeout=30,
        )
        return json.loads(result.stdout)

    def test_prepared_request_is_consumed_and_rebuilt_as_fixed_demo(self):
        with tempfile.TemporaryDirectory() as td:
            runtime, shared, profile = self.fixture(pathlib.Path(td))
            client = shared / "libraries" / CLIENT_PATH
            client.unlink()
            blocked = self.call_host("prepare", runtime, shared)
            self.assertFalse(blocked["ok"])
            self.assertIn("missing", blocked["error"].lower())
            self.assertFalse((runtime / "tmp/minecraft-launch-request.json").exists())
            client.write_bytes(b"client fixture")

            queued = self.call_host("prepare", runtime, shared)
            self.assertTrue(queued["ok"], queued)
            queue_path = runtime / "tmp/minecraft-launch-request.json"
            queue = json.loads(queue_path.read_text())
            self.assertEqual(set(queue), {"schema_version", "instance_id", "mode", "shared_root", "version", "game_directory"})
            self.assertEqual(queue["mode"], "official-demo")
            # Queue data cannot replace the launcher's fixed main, classpath, args, or VM flags.
            queue.update({"main_class": "evil.Main", "classpath": "evil.jar", "arguments": ["--accessToken", "secret"], "options": ["-Xmx999G"]})
            queue_path.write_text(json.dumps(queue))
            launch = self.call_host("consume", runtime, shared)
            self.assertTrue(launch["ok"], launch)
            self.assertEqual(launch["main_class"], "net/minecraft/client/main/Main")
            self.assertIn("switchcraft-lwjgl-horizon.jar", launch["classpath"])
            self.assertIn("switchcraft-launcher-bridge.jar", launch["classpath"])
            self.assertIn(";", launch["classpath"])
            self.assertEqual(launch["heap_mib"], 768)
            self.assertEqual(launch["game_directory"], str(profile / ".minecraft"))
            self.assertEqual(launch["arguments"], [
                "--demo", "--graphicsBackend", "VULKAN", "--version", VERSION,
                "--accessToken", "", "--gameDir", str(profile / ".minecraft"),
                "--assetsDir", str(shared / "assets"), "--assetIndex", "36",
            ])
            self.assertIn("-Xms64M", launch["options"])
            self.assertIn("-Xmx768M", launch["options"])
            self.assertIn("-Djava.awt.headless=true", launch["options"])
            self.assertIn("-Dorg.lwjgl.system.allocator=system", launch["options"])
            self.assertTrue(any(option.startswith("-javaagent:") for option in launch["options"]))
            self.assertEqual(self.call_host("consume", runtime, shared)["ok"], False)
            self.assertFalse(queue_path.exists())

    def test_stale_settings_request_is_consumed_without_launch(self):
        with tempfile.TemporaryDirectory() as td:
            runtime, shared, _ = self.fixture(pathlib.Path(td))
            self.assertTrue(self.call_host("prepare", runtime, shared)["ok"])
            other = pathlib.Path(td) / "other"
            other.mkdir()
            cfg = json.loads((runtime / "config/launcher.json").read_text())
            cfg["minecraft_root"] = str(other)
            (runtime / "config/launcher.json").write_text(json.dumps(cfg))
            result = self.call_host("consume", runtime, shared)
            self.assertFalse(result["ok"])
            self.assertIn("no longer matches", result["error"])
            self.assertFalse((runtime / "tmp/minecraft-launch-request.json").exists())

    def test_malformed_request_is_consumed_without_launch(self):
        with tempfile.TemporaryDirectory() as td:
            runtime, shared, _ = self.fixture(pathlib.Path(td))
            self.assertTrue(self.call_host("prepare", runtime, shared)["ok"])
            queue_path = runtime / "tmp/minecraft-launch-request.json"
            queue_path.write_text('{"schema_version":')
            result = self.call_host("consume", runtime, shared)
            self.assertFalse(result["ok"])
            self.assertFalse(queue_path.exists())


if __name__ == "__main__":
    unittest.main()
