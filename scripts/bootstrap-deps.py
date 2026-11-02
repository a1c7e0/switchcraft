#!/usr/bin/env python3
"""Fetch hash-locked public dependencies; apply the reviewable Horizon patch."""
import hashlib
import json
import pathlib
import shutil
import subprocess
import tarfile
import urllib.request
import os

ROOT=pathlib.Path(__file__).resolve().parents[1]
DEPS=ROOT/".deps"
LOCK=json.loads((ROOT/"dependencies.lock.json").read_text())

def download(name):
    entry=LOCK[name]
    archive=DEPS/(name+".archive")
    if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest()!=entry["sha256"]:
        print("Downloading",name,flush=True)
        partial=archive.with_suffix(".partial")
        urllib.request.urlretrieve(entry["url"],partial)
        assert hashlib.sha256(partial.read_bytes()).hexdigest()==entry["sha256"],name+" checksum mismatch"
        partial.replace(archive)
    return archive

def extract(archive,dest,strip=False,prefix=None):
    dest.mkdir(parents=True,exist_ok=True)
    with tarfile.open(archive) as tar:
        for member in tar:
            name=member.name.split('/',1)[-1] if strip else member.name
            if prefix and not name.startswith(prefix):continue
            member.name=name
            tar.extract(member,dest,filter="data")

def main():
    DEPS.mkdir(exist_ok=True)
    if not (DEPS/"nvk/lib/libvulkan.a").exists():extract(download("nvk"),DEPS/"nvk")
    assert hashlib.sha256((DEPS/"nvk/lib/libvulkan.a").read_bytes()).hexdigest()==LOCK["nvk"]["library_sha256"]
    if not (DEPS/"nvk/include/vk_video").exists():
        extract(download("vulkan_headers"),DEPS/"vk-headers",True)
        shutil.copytree(DEPS/"vk-headers/include/vk_video",DEPS/"nvk/include/vk_video",dirs_exist_ok=True)
    entry=LOCK['java_switch']
    target=pathlib.Path(os.environ.get('JAVA_SWITCH_SOURCE',str(DEPS/'java-switch')))
    created=not target.exists()
    if created:subprocess.run(['git','clone','--no-checkout','--depth','1',entry['url'],str(target)],check=True)
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=target,text=True).strip()
    if created or revision!=entry['revision']:
        subprocess.run(['git','fetch','--depth','1','origin',entry['revision']],cwd=target,check=True)
        subprocess.run(['git','checkout','--detach',entry['revision']],cwd=target,check=True)
    if subprocess.check_output(['git','status','--porcelain'],cwd=target,text=True).strip():raise RuntimeError('Java dependency has uncommitted changes')
    # Share hash-verified downloads/toolchain on constrained build machines.
    if not (target/'.deps').exists():(target/'.deps').symlink_to(DEPS,target_is_directory=True)
    if not (target/'.toolchain').exists():(target/'.toolchain').symlink_to(ROOT/'.toolchain',target_is_directory=True)
    assert hashlib.sha256((ROOT/"vendor/json.hpp").read_bytes()).hexdigest()==LOCK["nlohmann_json"]["sha256"]
    print("Dependencies verified")

if __name__=="__main__":main()
