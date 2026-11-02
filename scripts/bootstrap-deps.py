#!/usr/bin/env python3
"""Fetch hash-locked public dependencies; apply the reviewable Horizon patch."""
import hashlib
import json
import pathlib
import shutil
import subprocess
import tarfile
import urllib.request

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
    patch=ROOT/"patches/minijvm-horizon.patch"
    patch_hash=hashlib.sha256(patch.read_bytes()+(ROOT/"src/minijvm_mman.h").read_bytes()).hexdigest()
    stamp=DEPS/"minijvm-patch.sha256"
    if not stamp.exists() or stamp.read_text()!=patch_hash:
        source=DEPS/"minijvm-source"
        extract(download("minijvm"),source,True,prefix="minijvm/")
        # Root notices are retained alongside the complete Java class-library source.
        with tarfile.open(download("minijvm")) as archive:
            member=next(m for m in archive if m.name.endswith('/LICENSE') and m.name.count('/')==1)
            (source/"LICENSE").write_bytes(archive.extractfile(member).read())
        target=DEPS/"minijvm"
        if target.exists():shutil.rmtree(target)
        shutil.copytree(source/"minijvm/c",target)
        subprocess.run(["patch","--batch","-p1","-i",str(patch)],cwd=target,check=True)
        shutil.copyfile(ROOT/"src/minijvm_mman.h",target/"jvm/sc_mman.h")
        stamp.write_text(patch_hash)
    if not (DEPS/"host-jdk8/jdk8u504-b01/bin/javac").exists():extract(download("host_jdk8"),DEPS/"host-jdk8")
    assert hashlib.sha256((ROOT/"vendor/json.hpp").read_bytes()).hexdigest()==LOCK["nlohmann_json"]["sha256"]
    print("Dependencies verified")

if __name__=="__main__":main()
