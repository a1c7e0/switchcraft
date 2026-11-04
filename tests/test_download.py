import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import shlex
import ssl
import subprocess
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Handler(BaseHTTPRequestHandler):
    counts = {}
    bodies = {"/file": b"verified artifact payload", "/text": b'{"ok":true}'}

    def do_GET(self):
        self.counts[self.path] = self.counts.get(self.path, 0) + 1
        if self.path == "/retry" and self.counts[self.path] == 1:
            body = b"partial"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body) + 20))
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
            self.close_connection = True
            self.connection.shutdown(1)
            return
        if self.path not in self.bodies and self.path != "/retry":
            self.send_error(404)
            return
        body = b"clean retry payload" if self.path == "/retry" else self.bodies[self.path]
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


class DownloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.build.name) / "download-host"
        flags = subprocess.check_output(["pkg-config", "--cflags", "--libs", "libcurl", "openssl"], text=True)
        subprocess.run(["g++", "-std=c++17", "-O2", "-I", str(ROOT / "src"),
                        str(ROOT / "src/download.cpp"), str(ROOT / "tests/download_host.cpp"),
                        "-o", str(cls.binary), *shlex.split(flags)], check=True)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.tls_build = tempfile.TemporaryDirectory()
        tls_dir = Path(cls.tls_build.name)
        cls.cert = tls_dir / "cert.pem"
        cls.key = tls_dir / "key.pem"
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(cls.key),
                        "-out", str(cls.cert), "-days", "1", "-subj", "/CN=localhost",
                        "-addext", "subjectAltName=IP:127.0.0.1,DNS:localhost"],
                       check=True, capture_output=True)
        cls.tls_server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls_context.load_cert_chain(cls.cert, cls.key)
        cls.tls_server.socket = tls_context.wrap_socket(cls.tls_server.socket, server_side=True)
        cls.tls_thread = threading.Thread(target=cls.tls_server.serve_forever, daemon=True)
        cls.tls_thread.start()
        cls.tls_base = f"https://127.0.0.1:{cls.tls_server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.tls_server.shutdown()
        cls.tls_server.server_close()
        cls.tls_thread.join(timeout=3)
        cls.tls_build.cleanup()
        cls.build.cleanup()

    def call(self, *args):
        return subprocess.run([str(self.binary), *map(str, args)], capture_output=True, text=True, timeout=20)

    def download_args(self, url, target, payload, algo="sha256", retries=0, *extra):
        digest = hashlib.new(algo, payload).hexdigest()
        return ("download", url, target, algo, digest, len(payload), len(payload) + 10, retries, "http-test", *extra)

    def test_hash_verified_download_retries_from_clean_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "artifact.jar"
            payload = b"clean retry payload"
            before = Handler.counts.get("/retry", 0)
            result = self.call(*self.download_args(self.base + "/retry", target, payload, retries=1))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(target.read_bytes(), payload)
            self.assertFalse(Path(str(target) + ".part").exists())
            self.assertFalse(Path(str(target) + ".part.owner").exists())
            self.assertIn("attempts=2", result.stdout)
            self.assertEqual(Handler.counts["/retry"] - before, 2)

    def test_sha1_mismatch_does_not_publish_and_valid_destination_is_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "artifact.jar"
            args = list(self.download_args(self.base + "/file", target, b"wrong expected body", algo="sha1"))
            args[4] = hashlib.sha1(b"bad digest").hexdigest()
            result = self.call(*args)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())
            self.assertFalse(Path(str(target) + ".part.owner").exists())
            self.assertFalse(Path(str(target) + ".part").exists())
            payload = Handler.bodies["/file"]
            good = self.call(*self.download_args(self.base + "/file", target, payload, algo="sha1"))
            self.assertEqual(good.returncode, 0, good.stderr)
            cached = self.call(*self.download_args(self.base + "/missing", target, payload, algo="sha1"))
            self.assertEqual(cached.returncode, 0, cached.stderr)
            self.assertIn("from_cache=1", cached.stdout)

    def test_corrupt_existing_file_is_preserved_unless_repair_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "artifact.jar"
            target.write_bytes(b"user data")
            payload = Handler.bodies["/file"]
            args = self.download_args(self.base + "/file", target, payload)
            refused = self.call(*args)
            self.assertNotEqual(refused.returncode, 0)
            self.assertEqual(target.read_bytes(), b"user data")
            repaired = self.call(*self.download_args(self.base + "/file", target, payload, "sha256", 0, "repair"))
            self.assertEqual(repaired.returncode, 0, repaired.stderr)
            self.assertEqual(target.read_bytes(), payload)
            self.assertFalse(Path(str(target) + ".corrupt").exists())

    def test_cancellation_and_stale_part_leave_destination_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "artifact.jar"
            payload = Handler.bodies["/file"]
            cancelled = self.call(*self.download_args(self.base + "/file", target, payload, "sha256", 2, "", 1))
            self.assertNotEqual(cancelled.returncode, 0)
            self.assertIn("cancelled", cancelled.stderr.lower())
            self.assertFalse(target.exists())
            callback_cancelled = self.call(*self.download_args(self.base + "/file", target, payload, "sha256", 2, "", "cancel-callback"))
            self.assertNotEqual(callback_cancelled.returncode, 0)
            self.assertIn("cancelled", callback_cancelled.stderr.lower())
            self.assertFalse(target.exists())
            part = Path(str(target) + ".part")
            part.write_text("unowned")
            blocked = self.call(*self.download_args(self.base + "/file", target, payload, "sha256", 0, "repair"))
            self.assertNotEqual(blocked.returncode, 0)
            self.assertEqual(part.read_text(), "unowned")

    def test_owned_stale_partial_requires_repair_and_clean_restarts(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "artifact.jar"
            payload = Handler.bodies["/file"]
            digest = hashlib.sha256(payload).hexdigest()
            part = Path(str(target) + ".part")
            owner = Path(str(part) + ".owner")
            part.write_bytes(b"partial from previous power loss")
            owner.write_text(f"switchcraft-part-v1\nsha256\n{digest}\n{len(payload)}\n")
            refused = self.call(*self.download_args(self.base + "/file", target, payload))
            self.assertNotEqual(refused.returncode, 0)
            self.assertTrue(part.exists())
            recovered = self.call(*self.download_args(self.base + "/file", target, payload, "sha256", 0, "repair"))
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            self.assertEqual(target.read_bytes(), payload)
            self.assertFalse(part.exists())
            self.assertFalse(owner.exists())

    def test_mismatched_or_symlink_partial_journal_is_never_repaired(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "artifact.jar"
            payload = Handler.bodies["/file"]
            part = Path(str(target) + ".part")
            owner = Path(str(part) + ".owner")
            part.write_bytes(b"unowned partial")
            owner.write_text("switchcraft-part-v1\nsha256\n" + "0" * 64 + f"\n{len(payload)}\n")
            mismatch = self.call(*self.download_args(self.base + "/file", target, payload, "sha256", 0, "repair"))
            self.assertNotEqual(mismatch.returncode, 0)
            self.assertEqual(part.read_bytes(), b"unowned partial")
            owner.unlink()
            outside = Path(tmp) / "outside"
            outside.write_text("foreign owner")
            owner.symlink_to(outside)
            symlink = self.call(*self.download_args(self.base + "/file", target, payload, "sha256", 0, "repair"))
            self.assertNotEqual(symlink.returncode, 0)
            self.assertEqual(part.read_bytes(), b"unowned partial")
            self.assertEqual(outside.read_text(), "foreign owner")

    def test_bounded_text_and_https_only_default(self):
        too_large = self.call("fetch", self.base + "/text", 4, "http-test")
        self.assertNotEqual(too_large.returncode, 0)
        rejected_http = self.call("fetch", self.base + "/text", 100)
        self.assertNotEqual(rejected_http.returncode, 0)
        accepted_test_http = self.call("fetch", self.base + "/text", 100, "http-test")
        self.assertEqual(accepted_test_http.returncode, 0, accepted_test_http.stderr)
        self.assertEqual(accepted_test_http.stdout, '{"ok":true}')
        source = (ROOT / "src/download.cpp").read_text()
        self.assertIn("setopt(CURLOPT_SSL_VERIFYPEER, 1L)", source)
        self.assertIn("setopt(CURLOPT_SSL_VERIFYHOST, 2L)", source)
        self.assertNotIn("CURLOPT_SSL_VERIFYPEER, 0L", source)
        self.assertIn("setopt(CURLOPT_CAINFO, ca_bundle.c_str())", source)

    def test_tls_rejects_untrusted_certificate_and_accepts_configured_ca(self):
        untrusted = self.call("fetch", self.tls_base + "/text", 100)
        self.assertNotEqual(untrusted.returncode, 0)
        trusted = self.call("fetch", self.tls_base + "/text", 100, "https-test", self.cert)
        self.assertEqual(trusted.returncode, 0, trusted.stderr)
        self.assertEqual(trusted.stdout, '{"ok":true}')

    def test_transport_shutdown_allows_clean_reinitialization(self):
        result = self.call("fetch-restart", self.tls_base + "/text", 100, "https-test", self.cert)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '{"ok":true}')

    def test_read_only_local_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "artifact"
            payload = b"local integrity check"
            path.write_bytes(payload)
            valid = self.call("verify", path, "sha256", hashlib.sha256(payload).hexdigest())
            invalid = self.call("verify", path, "sha1", hashlib.sha1(b"wrong").hexdigest())
            self.assertEqual(valid.returncode, 0, valid.stderr)
            self.assertEqual(invalid.returncode, 3)
            self.assertEqual(path.read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()
