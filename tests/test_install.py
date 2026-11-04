import hashlib
import json
import pathlib
import shlex
import shutil
import subprocess
import tempfile
import threading
import http.server
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
VERSION='26.4-snapshot-6'
REAL=ROOT/'tests/fixtures/prism/real'

def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
def jbytes(value): return json.dumps(value,separators=(',',':')).encode()

class InstallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build=tempfile.TemporaryDirectory();cls.bin=pathlib.Path(cls.build.name)/'install-host'
        curl=shlex.split(subprocess.check_output(['pkg-config','--cflags','--libs','libcurl'],text=True))
        cmd=['g++','-std=c++17','-O1','-I'+str(ROOT/'vendor'),'-I'+str(ROOT/'src'),
             str(ROOT/'src/metadata.cpp'),str(ROOT/'src/prism_metadata.cpp'),str(ROOT/'src/download.cpp'),str(ROOT/'src/install.cpp'),str(ROOT/'tests/install_host.cpp'),'-lcrypto',*curl,'-o',str(cls.bin)]
        subprocess.run(cmd,check=True)
    @classmethod
    def tearDownClass(cls):cls.build.cleanup()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.dir=pathlib.Path(self.tmp.name);self.web=self.dir/'web';self.counts={}
        self.client=b'fake-client-jar';self.lib=b'common-library';self.lwjgl=b'lwjgl-library';self.asset=b'asset-payload'
        write(self.web/'blobs/client.jar',self.client);write(self.web/'blobs/lib.jar',self.lib);write(self.web/'blobs/lwjgl.jar',self.lwjgl)
        ah=hashlib.sha1(self.asset).hexdigest();asset_index=jbytes({'objects':{'test':{'hash':ah,'size':len(self.asset)}}});write(self.web/'blobs/assets.json',asset_index);write(self.web/'assets'/ah[:2]/ah,self.asset)
        mc={'formatVersion':1,'uid':'net.minecraft','version':VERSION,'type':'snapshot','mainClass':'Main','compatibleJavaMajors':[25],
            'mainJar':{'name':f'com.mojang:minecraft:{VERSION}:client','downloads':{'artifact':{'url':'http://HOST/blobs/client.jar','sha1':hashlib.sha1(self.client).hexdigest(),'size':len(self.client)}}},
            'assetIndex':{'id':'test','url':'http://HOST/blobs/assets.json','sha1':hashlib.sha1(asset_index).hexdigest(),'size':len(asset_index)},
            'requires':[{'uid':'org.lwjgl3','suggests':'3.4.3'}],
            'libraries':[{'name':'org.example:common:1.0','downloads':{'artifact':{'path':'org/example/common/1.0/common-1.0.jar','url':'http://HOST/blobs/lib.jar','sha1':hashlib.sha1(self.lib).hexdigest(),'size':len(self.lib)}}},
                         {'name':'org.example:desktop:1.0','downloads':{'artifact':{'path':'org/example/desktop/1.0/desktop-1.0.jar','url':'http://HOST/blobs/lib.jar','sha1':hashlib.sha1(self.lib).hexdigest(),'size':len(self.lib)}},'rules':[{'action':'allow','os':{'name':'windows'}}]}]}
        lw={'formatVersion':1,'uid':'org.lwjgl3','version':'3.4.3','libraries':[{'name':'org.lwjgl:lwjgl:3.4.3','downloads':{'artifact':{'path':'org/lwjgl/lwjgl/3.4.3/lwjgl-3.4.3.jar','url':'http://HOST/blobs/lwjgl.jar','sha1':hashlib.sha1(self.lwjgl).hexdigest(),'size':len(self.lwjgl)}}},
            {'name':'org.lwjgl:lwjgl-natives-windows:3.4.3','downloads':{'artifact':{'path':'org/lwjgl/lwjgl/3.4.3/lwjgl-3.4.3-natives-windows.jar','url':'http://HOST/blobs/lib.jar','sha1':hashlib.sha1(self.lib).hexdigest(),'size':len(self.lib)}},'rules':[{'action':'allow','os':{'name':'windows'}}]}]}
        for uid,meta in [('net.minecraft',mc),('org.lwjgl3',lw)]:
            raw=jbytes(meta);write(self.web/f'v1/{uid}/{meta["version"]}.json',raw)
            index=jbytes({'formatVersion':1,'uid':uid,'versions':[{'version':meta['version'],'type':'snapshot','releaseTime':'2026-11-01T00:00:00Z','recommended':False,'sha256':hashlib.sha256(raw).hexdigest()}]})
            write(self.web/f'v1/{uid}/index.json',index)
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(inner):
                rel=inner.path.split('?',1)[0].lstrip('/');self.counts[rel]=self.counts.get(rel,0)+1
                if rel=='blobs/client.jar' and self.counts[rel]==1: data=b'first-response-corrupt'
                else:
                    p=self.web/rel
                    if not p.is_file():inner.send_error(404);return
                    data=p.read_bytes()
                inner.send_response(200);inner.send_header('Content-Length',str(len(data)));inner.end_headers();inner.wfile.write(data)
            def log_message(inner,*args):pass
        self.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_address[1]}/v1';self.assets=f'http://127.0.0.1:{self.server.server_address[1]}/assets';
        for p in self.web.rglob('*'):
            if p.is_file():
                raw=p.read_bytes()
                if b'HOST' in raw: p.write_bytes(raw.replace(b'HOST',f'127.0.0.1:{self.server.server_address[1]}'.encode()))
        for uid in ('net.minecraft','org.lwjgl3'):
            meta_path=self.web/f'v1/{uid}/{VERSION if uid=="net.minecraft" else "3.4.3"}.json'
            raw=meta_path.read_bytes();idx_path=self.web/f'v1/{uid}/index.json';idx=json.loads(idx_path.read_text())
            idx['versions'][0]['sha256']=hashlib.sha256(raw).hexdigest();idx_path.write_bytes(jbytes(idx))
        self.root=self.dir/'shared';(self.root/'saves/world').mkdir(parents=True);self.save=self.root/'saves/world/level.dat';self.save.write_bytes(b'user save')
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
    def runhost(self,action,repair='no'):
        p=subprocess.run([str(self.bin),str(self.root),action,self.base,self.assets,VERSION,repair],text=True,capture_output=True)
        if p.stdout.strip(): return p,json.loads(p.stdout)
        return p,{}
    def test_full_refresh_download_filter_deduplicate_verify_and_retry(self):
        p,r=self.runhost('install')
        self.assertEqual(p.returncode,0,p.stderr or r);self.assertEqual(r['status'],'verified')
        self.assertGreaterEqual(self.counts.get('blobs/client.jar',0),2) # first response fails SHA-1, retry succeeds
        self.assertTrue((self.root/f'libraries/com/mojang/minecraft/{VERSION}/minecraft-{VERSION}-client.jar').is_file())
        self.assertTrue((self.root/'libraries/org/example/common/1.0/common-1.0.jar').is_file())
        self.assertTrue((self.root/'libraries/org/lwjgl/lwjgl/3.4.3/lwjgl-3.4.3.jar').is_file())
        self.assertFalse((self.root/'libraries/org/example/desktop/1.0/desktop-1.0.jar').exists())
        self.assertTrue((self.root/'assets/objects'/hashlib.sha1(self.asset).hexdigest()[:2]/hashlib.sha1(self.asset).hexdigest()).is_file())
        self.assertEqual(self.save.read_bytes(),b'user save')
        receipt=self.root/f'meta/net.minecraft/{VERSION}.installed.json';self.assertTrue(receipt.is_file());self.assertTrue(json.loads(receipt.read_text())['installed'])
        p,v=self.runhost('verify');self.assertEqual(p.returncode,0,p.stderr);self.assertTrue(v['details']['installed'])
        p,v=self.runhost('verifycancel');self.assertNotEqual(p.returncode,0);self.assertTrue(v['cancelled'])
        bad=self.root/'libraries/org/example/common/1.0/common-1.0.jar';bad.write_bytes(b'corrupt')
        p,v=self.runhost('verify');self.assertNotEqual(p.returncode,0);self.assertIn('corrupt_files',v['details'])
    def test_corrupt_cache_preserved_until_explicit_repair(self):
        p,r=self.runhost('install');self.assertEqual(p.returncode,0,p.stderr or r)
        target=self.root/f'libraries/com/mojang/minecraft/{VERSION}/minecraft-{VERSION}-client.jar';target.write_bytes(b'preexisting corruption')
        p,r=self.runhost('install');self.assertNotEqual(p.returncode,0);self.assertEqual(target.read_bytes(),b'preexisting corruption')
        p,r=self.runhost('install','repair');self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(target.read_bytes(),self.client)
    def test_cancellation_and_unrelated_files(self):
        p,r=self.runhost('cancel');self.assertNotEqual(p.returncode,0);self.assertTrue(r['cancelled']);self.assertEqual(self.save.read_bytes(),b'user save')
        self.assertFalse((self.root/f'meta/net.minecraft/{VERSION}.installed.json').exists())
    def test_metadata_stage_symlink_cannot_clobber_save(self):
        meta=self.root/'meta/net.minecraft';meta.mkdir(parents=True)
        stage=meta/'index.json.new';stage.symlink_to(self.save)
        before=self.save.read_bytes()
        p,r=self.runhost('refresh')
        self.assertEqual(p.returncode,0,p.stderr or r)
        self.assertTrue(stage.is_symlink())
        self.assertEqual(self.save.read_bytes(),before)
        self.assertTrue((meta/'index.json').is_file())
    def test_receipt_symlink_is_refused_without_touching_save(self):
        p,r=self.runhost('install');self.assertEqual(p.returncode,0,p.stderr or r)
        receipt=self.root/f'meta/net.minecraft/{VERSION}.installed.json';receipt.unlink();receipt.symlink_to(self.save)
        before=self.save.read_bytes()
        p,r=self.runhost('install')
        self.assertNotEqual(p.returncode,0)
        self.assertIn('non-regular managed metadata target',r['details']['error'])
        self.assertTrue(receipt.is_symlink());self.assertEqual(self.save.read_bytes(),before)
    def test_refresh_real_prism_target_and_suggested_dependency(self):
        shutil.copy(REAL/'net.minecraft.json',self.web/f'v1/net.minecraft/{VERSION}.json')
        shutil.copy(REAL/'net.minecraft-index.json',self.web/'v1/net.minecraft/index.json')
        raw=(REAL/'org.lwjgl3.json').read_bytes();shutil.copy(REAL/'org.lwjgl3.json',self.web/'v1/org.lwjgl3/3.4.3.json')
        idx=jbytes({'formatVersion':1,'uid':'org.lwjgl3','versions':[{'version':'3.4.3','type':'release','releaseTime':'2026-10-01T00:00:00Z','recommended':True,'sha256':hashlib.sha256(raw).hexdigest()}]})
        write(self.web/'v1/org.lwjgl3/index.json',idx)
        p,r=self.runhost('refresh')
        self.assertEqual(p.returncode,0,p.stderr or r)
        self.assertEqual(r['details']['version'],VERSION)
        self.assertEqual(r['details']['dependencies'][0]['version'],'3.4.3')
        self.assertEqual(hashlib.sha256((self.root/f'meta/net.minecraft/{VERSION}.json').read_bytes()).hexdigest(),r['details']['minecraft_metadata_sha256'])
    def test_refresh_requires_explicit_test_mirror_option(self):
        # The public API refuses arbitrary endpoint overrides by default; test mirror opt-in is a separate explicit flag.
        p=subprocess.run([str(self.bin),str(self.root),'badmirror',self.base,self.assets,VERSION],text=True,capture_output=True)
        self.assertNotEqual(p.returncode,0)
