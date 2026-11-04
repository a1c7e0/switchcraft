import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("prism_cache", ROOT / "tools/prism-cache.py")
prism_cache = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prism_cache)


class Response:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, size=-1):
        return self.data[:size]


def encoded(value):
    return json.dumps(value, separators=(",", ":")).encode()


class PrismCacheTests(unittest.TestCase):
    def test_hash_verified_cache_and_suggested_dependency(self):
        mc = {"uid": "net.minecraft", "version": "26.4-snapshot-6", "requires": [{"uid": "org.lwjgl3", "suggests": "3.4.3"}]}
        lwjgl = {"uid": "org.lwjgl3", "version": "3.4.3", "requires": []}
        mc_bytes, lwjgl_bytes = encoded(mc), encoded(lwjgl)
        responses = {
            f"{prism_cache.BASE_URL}/net.minecraft/index.json": encoded({"formatVersion": 1, "versions": [{"version": "26.4-snapshot-6", "sha256": hashlib.sha256(mc_bytes).hexdigest()}]}),
            f"{prism_cache.BASE_URL}/net.minecraft/26.4-snapshot-6.json": mc_bytes,
            f"{prism_cache.BASE_URL}/org.lwjgl3/index.json": encoded({"formatVersion": 1, "versions": [
                {"version": "3.4.2", "recommended": True, "sha256": "0" * 64},
                {"version": "3.4.3", "sha256": hashlib.sha256(lwjgl_bytes).hexdigest()},
            ]}),
            f"{prism_cache.BASE_URL}/org.lwjgl3/3.4.3.json": lwjgl_bytes,
        }

        def fake_open(url, timeout):
            self.assertEqual(timeout, 30)
            return Response(responses[url])

        with tempfile.TemporaryDirectory() as tmp, patch.object(prism_cache, "urlopen", fake_open):
            root = prism_cache.cache(Path(tmp) / "cache", "26.4-snapshot-6")
            self.assertEqual(json.loads((root / "meta/net.minecraft/26.4-snapshot-6.json").read_bytes()), mc)
            self.assertTrue((root / "meta/net.minecraft/index.json").is_file())
            self.assertTrue((root / "meta/org.lwjgl3/3.4.3.json").is_file())
            self.assertFalse((root / "meta/org.lwjgl3/3.4.2.json").exists())

    def test_hash_mismatch_never_publishes_version(self):
        metadata = encoded({"uid": "net.minecraft", "version": "v1"})
        responses = {
            f"{prism_cache.BASE_URL}/net.minecraft/index.json": encoded({"formatVersion": 1, "versions": [{"version": "v1", "sha256": "0" * 64}]}),
            f"{prism_cache.BASE_URL}/net.minecraft/v1.json": metadata,
        }
        with tempfile.TemporaryDirectory() as tmp, patch.object(prism_cache, "urlopen", lambda url, timeout: Response(responses[url])):
            root = Path(tmp) / "cache"
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                prism_cache.cache(root, "v1")
            self.assertFalse((root / "meta/net.minecraft/v1.json").exists())

    def test_existing_different_metadata_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "meta/net.minecraft/v1.json"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"original")
            with self.assertRaises(FileExistsError):
                prism_cache.publish(root, "net.minecraft", "v1.json", b"replacement", hashlib.sha256(b"replacement").hexdigest())
            self.assertEqual(target.read_bytes(), b"original")

    def test_path_and_token_rejections(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                prism_cache.cache(Path(tmp) / "cache", "../escape")
            dist_root = ROOT / "dist" / "prism-cache-test"
            with self.assertRaisesRegex(ValueError, "outside"):
                prism_cache.ensure_cache_root(dist_root)
            with self.assertRaises(ValueError):
                prism_cache.publish(Path(tmp), "../outside", "v1.json", b"{}")


if __name__ == "__main__":
    unittest.main()
