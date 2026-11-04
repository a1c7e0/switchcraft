#!/usr/bin/env python3
"""Fetch the exact static curl source used by the pinned Switch package."""
import hashlib,json,tempfile,os
from pathlib import Path
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
def prepare():
    record=json.loads((ROOT/'vendor/curl/UPSTREAM.json').read_text())
    for name,key in [('PKGBUILD','recipe_sha256'),('switch-curl.patch','patch_sha256')]:
        if hashlib.sha256((ROOT/'vendor/curl'/name).read_bytes()).hexdigest()!=record[key]:raise ValueError('curl recipe/patch hash mismatch')
    dest=ROOT/'.deps/curl-7.69.1.tar.xz';dest.parent.mkdir(exist_ok=True)
    if not dest.exists():
        bundled=ROOT.parent/'third-party/curl-7.69.1.tar.xz'
        raw=bundled.read_bytes() if bundled.is_file() else urllib.request.urlopen(record['source_url'],timeout=90).read(16*1024*1024+1)
        if hashlib.sha256(raw).hexdigest()!=record['source_sha256']:raise ValueError('curl source checksum mismatch')
        with tempfile.NamedTemporaryFile(dir=dest.parent,prefix='curl-source-',delete=False) as stream:
            partial=Path(stream.name);stream.write(raw)
        try:os.replace(partial,dest)
        finally:partial.unlink(missing_ok=True)
    if hashlib.sha256(dest.read_bytes()).hexdigest()!=record['source_sha256']:raise ValueError('cached curl source checksum mismatch')
    return dest
if __name__=='__main__':print(prepare())
