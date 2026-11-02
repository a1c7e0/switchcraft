#!/usr/bin/env python3
"""Validate the NRO container, metadata and matching AArch64 linked ELF."""
import hashlib
import json
import pathlib
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
APPS = ("switch-diagnostics", "vulkan-test", "vulkan-present", "minecraft-launcher", "java-test", "ffi-test")

def verify(nro, elf):
    data = pathlib.Path(nro).read_bytes()
    linked = pathlib.Path(elf).read_bytes()
    assert len(linked) > 64 and linked[:6] == b"\x7fELF\x02\x01", "ELF64 little endian required"
    assert struct.unpack_from("<HH", linked, 16) == (3, 183), "AArch64 PIE required"
    assert len(data) > 0x80 and data[0x10:0x14] == b"NRO0", "NRO0 header missing"
    version, size, flags = struct.unpack_from("<III", data, 0x14)
    assert version == 0 and size % 4096 == 0 and size < len(data), "Invalid NRO size/version"
    segments = [struct.unpack_from("<II", data, 0x20 + 8*i) for i in range(3)]
    assert segments[0][0] == 0 and segments[0][1] >= 0x80, "Invalid text segment"
    end = 0
    for offset, length in segments:
        assert offset % 4096 == 0 and length % 4096 == 0, "Unaligned NRO segment"
        assert offset >= end and length > 0 and offset + length <= size, "Invalid NRO segment range"
        end = offset + length
    assert end == size and any(data[0x40:0x60]), "Missing build ID or invalid data segment"
    assert data[size:size+4] == b"ASET" and len(data) >= size+56, "Missing asset header"
    assert struct.unpack_from("<I", data, size+4)[0] == 0, "Invalid ASET version"
    icon_off, icon_len, nacp_off, nacp_len, romfs_off, romfs_len = struct.unpack_from("<6Q", data, size+8)
    for off, length in [(icon_off, icon_len), (nacp_off, nacp_len), (romfs_off, romfs_len)]:
        if length:
            assert off >= 56 and size+off+length <= len(data), "Asset outside file"
    assert icon_len > 100 and data[size+icon_off:size+icon_off+2] == b"\xff\xd8", "JPEG icon required"
    assert nacp_len == 0x4000, "NACP metadata required"
    nacp = data[size+nacp_off:size+nacp_off+nacp_len]
    title = nacp[:0x200].split(b"\0")[0].decode()
    author = nacp[0x200:0x300].split(b"\0")[0].decode()
    external=title in ['java-test','ffi-test']
    assert title == pathlib.Path(nro).stem and author == ("JavaSwitch" if external else "Switchcraft"), "Unexpected NACP identity"
    assert nacp[0x3060:0x3070].split(b"\0")[0] == (b"0.2.0" if external else b"0.1.0"), "Missing app version"
    # Cross-check ELF GNU build ID against the NRO build ID, padded to 32 bytes.
    build_id = data[0x40:0x54]
    assert b"GNU\0" + build_id in linked, "ELF and NRO build IDs differ"
    return {"name": pathlib.Path(nro).name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "architecture": "AArch64", "format": "NRO0+ASET", "nacp_title": title, "build_id": build_id.hex(),
            "build_verification": "PASS", "hardware_verification": "NOT TESTED"}

def main():
    records = [verify(ROOT/"dist"/(app+".nro"), ROOT/"build"/(app+".elf")) for app in APPS]
    print(json.dumps(records, indent=2))

if __name__ == "__main__":
    try:
        main()
    except (AssertionError, OSError, ValueError, struct.error) as error:
        print("Artifact verification FAILED:", error, file=sys.stderr)
        sys.exit(1)
