#!/usr/bin/env python3
"""Build a genuine, deliberately limited static LWJGL 3.4.3 core JNI provider."""
import argparse
import hashlib
import json
import os
import pathlib
import platform
import re
import shutil
import shlex
import subprocess
import tarfile
import tempfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "dependencies.lock.json").read_text())
PIN = LOCK["lwjgl_core"]
REVISION = PIN["source_revision"]
ARCHIVE_URL = PIN["source_url"]
ARCHIVE_SHA256 = PIN["source_archive_sha256"]
if PIN["version"] != "3.4.3" or REVISION not in ARCHIVE_URL or not re.fullmatch(r"[0-9a-f]{64}", ARCHIVE_SHA256):
    raise RuntimeError("dependencies.lock.json has an incoherent LWJGL source pin")
def checked_archive() -> pathlib.Path:
    path = ROOT / ".deps/lwjgl_core_source.archive"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        tmp = path.with_suffix(".partial")
        urllib.request.urlretrieve(ARCHIVE_URL, tmp)
        if hashlib.sha256(tmp.read_bytes()).hexdigest() != ARCHIVE_SHA256:
            tmp.unlink(missing_ok=True)
            raise RuntimeError("pinned LWJGL source archive SHA-256 mismatch")
        tmp.replace(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise RuntimeError(f"pinned LWJGL source archive SHA-256 mismatch: {path}")
    return path


def compile_mode(mode: str, src: pathlib.Path, out: pathlib.Path) -> list[pathlib.Path]:
    out.mkdir(parents=True, exist_ok=True)
    include = ROOT / "build/java25-integrated/runtime/openjdk25-horizon-runtime/include"
    if not (include / "jni.h").is_file():
        raise RuntimeError("build the integrated Java 25 runtime first (JNI headers missing)")
    required_abi = "SYSV"
    if mode == "host":
        cc, nm, ar = shutil.which("cc"), shutil.which("nm"), shutil.which("ar")
        jni_include = ROOT / ".deps/host-jdk25/jdk-25.0.5+8/include"
        includes = [jni_include, jni_include / "linux"]
        flags = ["-fPIC", "-O2", "-pthread", "-DLWJGL_LINUX"]
        if platform.machine().lower() in ("x86_64", "amd64"):
            required_abi = "UNIX64"
        ffi_include, ffi_archive = build_private_host_libffi(out)
        includes = [*includes, ffi_include]
        ffi_cflags, ffi_libs = [], ["-Wl,--exclude-libs,ALL", str(ffi_archive), "-ldl"]
    else:
        devkit = pathlib.Path(os.environ.get("DEVKITPRO", ROOT / ".toolchain/opt/devkitpro"))
        prefix = devkit / "devkitA64/bin/aarch64-none-elf-"
        cc, nm, ar = (str(prefix.with_name(prefix.name + x)) for x in ("gcc", "nm", "ar"))
        sdk_include = ROOT / "build/java25-integrated/sdk/include"
        includes = [include, include / "horizon", sdk_include, devkit / "libnx/include"]
        flags = ["-march=armv8-a+crc+crypto", "-mtune=cortex-a57", "-mtp=soft",
                 "-mno-outline-atomics", "-fPIE", "-ffunction-sections", "-fdata-sections",
                 "-D__SWITCH__", "-DLWJGL_HORIZON", "-O2"]
        ffi_cflags, ffi_libs = [], []
    if not cc or not nm or not ar:
        raise RuntimeError(f"{mode}: compiler/nm/ar not found")
    module = src / "modules/lwjgl/core"
    common = module / "src/main/c"
    compat = out / "lwjgl_horizon_config.h"
    compat.write_text("""/* LWJGL warning macros; deliberately no Linux/Unix OS macro. */
#include <stdint.h>
#ifndef LWJGL_LINUX
#define DISABLE_WARNINGS() _Pragma(\"GCC diagnostic push\")
#define ENABLE_WARNINGS() _Pragma(\"GCC diagnostic pop\")
#endif
""")
    files = [module / "src/main/c/common_tools.c",
             module / "src/main/c/org_lwjgl_system_MemoryUtil.c",
             module / "src/main/c/org_lwjgl_system_ThreadLocalUtil.c",
             module / "src/main/c/org_lwjgl_system_Upcalls.c",
             *sorted((module / "src/generated/c").glob("*.c"))]
    if any(not source.is_file() for source in files):
        missing = [str(source) for source in files if not source.is_file()]
        raise RuntimeError("pinned LWJGL C source missing: " + ", ".join(missing))
    ffi_abis = supported_ffi_abis(cc, flags,
                                  [*includes, *[pathlib.Path(flag[2:]) for flag in ffi_cflags if flag.startswith("-I")]],
                                  required_abi)
    objects = []
    for source in files:
        obj = out / (source.stem + ".o")
        cmd = [cc, "-std=c11", *flags, *ffi_cflags, *[f"-DHAS_FFI_{abi}=1" for abi in ffi_abis],
               "-include", str(compat), "-I", str(common), "-I", str(common / "linux"),
               "-I", str(common / "windows"), "-I", str(common / "macosx"), "-I", str(common / "freebsd"),
               *(arg for path in includes for arg in ("-I", str(path))),
               "-D__USE_ISOC11",
               "-DJNI_OnLoad=JNI_OnLoad_lwjgl", "-DJNI_OnUnload=JNI_OnUnload_lwjgl",
               "-c", str(source), "-o", str(obj)]
        subprocess.run(cmd, check=True)
        objects.append(obj)

    symbols = set()
    for obj in objects:
        output = subprocess.check_output([nm, "-g", "--defined-only", str(obj)], text=True)
        for line in output.splitlines():
            match = re.search(r"\s[TW]\s+((?:Java_[A-Za-z0-9_]+)|(?:JNI_OnLoad_lwjgl)|(?:JNI_OnUnload_lwjgl))$", line)
            if match:
                symbols.add(match.group(1))
    if not symbols:
        raise RuntimeError("nm found no defined upstream JNI exports")
    # This include is the exact export inventory measured from these objects.
    inc = out / "lwjgl_core_exports.inc"
    rows = ["/* generated by scripts/build-lwjgl-core.py from nm output */",
            "struct sc_lwjgl_core_export { const char *name; void (*address)(void); };"]
    rows.extend(f"extern void {symbol}(void);" for symbol in sorted(symbols))
    rows.append("static const struct sc_lwjgl_core_export sc_lwjgl_core_exports[] = {")
    rows.extend(f'    {{"{symbol}", (void (*)(void)){symbol}}},' for symbol in sorted(symbols))
    rows.extend(["};", ""])
    inc.write_text("\n".join(rows))
    resolver = ROOT / "src/lwjgl_core_resolver.c"
    resolver_obj = out / "lwjgl_core_resolver.o"
    subprocess.run([cc, "-std=c11", *flags, "-I", str(ROOT / "include"), "-I", str(out),
                    "-c", str(resolver), "-o", str(resolver_obj)], check=True)
    archive = out / "liblwjgl-core.a"
    subprocess.run([ar, "rcs", str(archive), *(str(obj) for obj in [*objects, resolver_obj])], check=True)
    # A relocatable link catches duplicate definitions and proves resolver and
    # upstream JNI objects share the selected ABI. Runtime services resolve later.
    subprocess.run([cc, "-r", *(str(obj) for obj in [*objects, resolver_obj]), "-o", str(out / "lwjgl-core-link-proof.o")], check=True)
    if mode == "host":
        subprocess.run([cc, "-shared", "-pthread", *(str(obj) for obj in [*objects, resolver_obj]),
                        *ffi_libs, "-o", str(out / "liblwjgl.so")], check=True)
    java_count = sum(symbol.startswith("Java_") for symbol in symbols)
    lifecycle_count = len(symbols) - java_count
    print(f"{mode}: {java_count} genuine Java JNI exports + {lifecycle_count} lifecycle exports from {len(objects)} upstream C files; libffi ABIs={','.join(ffi_abis)} -> {archive}")
    return objects


def build_private_host_libffi(out: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    """Build pinned genuine libffi 3.8 privately for the host JNI reference.

    The archive is statically linked with --exclude-libs so its ffi_* symbols
    stay local to liblwjgl.so and cannot interpose on the JVM's own libffi.
    """
    pin = LOCK["libffi"]
    if pin.get("tag") != "v3.8.0":
        raise RuntimeError("host libffi pin must match the SDK's upstream v3.8.0")
    archive = ROOT / ".deps/libffi.archive"
    if not archive.is_file():
        urllib.request.urlretrieve(pin["url"], archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != pin["sha256"]:
        raise RuntimeError("pinned libffi source archive SHA-256 mismatch")
    source_root = ROOT / ".deps/lwjgl-core-libffi-source"
    source = source_root / "libffi-3.8.0"
    source_marker = source_root / ".archive-sha256"
    if not (source / "configure").is_file() or not source_marker.is_file() or source_marker.read_text().strip() != pin["sha256"]:
        shutil.rmtree(source_root, ignore_errors=True)
        source_root.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(source_root, filter="data")
        source_marker.write_text(pin["sha256"] + "\n")
    configure = source / "configure"
    build = out / "libffi-private"
    configured_pin = build / ".source-archive-sha256"
    valid_configuration = ((build / "Makefile").is_file() and configured_pin.is_file()
                           and configured_pin.read_text().strip() == pin["sha256"])
    if not valid_configuration:
        shutil.rmtree(build, ignore_errors=True)
        build.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(configure), "--disable-shared", "--enable-static", "--disable-docs", "--with-pic",
                        "CFLAGS=-O2 -fPIC"], cwd=build, check=True)
        configured_pin.write_text(pin["sha256"] + "\n")
    subprocess.run(["make", "-j4"], cwd=build, check=True)
    include = build / "include"
    lib_candidates = [build / ".libs/libffi.a", build / "src/.libs/libffi.a"]
    libffi = next((candidate for candidate in lib_candidates if candidate.is_file()), None)
    if not (include / "ffi.h").is_file() or libffi is None:
        raise RuntimeError("pinned libffi 3.8 host build did not produce ffi.h and libffi.a")
    return include, libffi


def supported_ffi_abis(cc: str, flags: list[str], include_dirs: list[pathlib.Path], required_abi: str) -> list[str]:
    """Probe ABI enum names in the exact host/system or Horizon SDK ffi.h."""
    candidates = ["SYSV", "UNIX64", "WIN64", "GNUW64", "EFI64", "STDCALL", "THISCALL",
                  "FASTCALL", "MS_CDECL", "PASCAL", "REGISTER", "VFP"]
    with tempfile.TemporaryDirectory(prefix="lwjgl-ffi-abi-") as temporary:
        directory = pathlib.Path(temporary)
        probe = directory / "abi.c"
        found = []
        for name in candidates:
            probe.write_text(f'#include "ffi.h"\nint probe(void) {{ return (int)FFI_{name}; }}\n')
            result = subprocess.run([cc, "-std=c11", *flags,
                                     *(arg for path in include_dirs for arg in ("-I", str(path))),
                                     "-Werror", "-c", str(probe), "-o", str(directory / "abi.o")],
                                    capture_output=True, text=True)
            if result.returncode == 0:
                found.append(name)
    if required_abi not in found:
        raise RuntimeError(f"selected libffi header lacks required FFI_{required_abi}; refusing to publish guessed ABI constants")
    return found


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", action="store_true", help="also build host JNI reference library")
    parser.add_argument("--cross", action="store_true", help="build Horizon AArch64 archive (default)")
    args = parser.parse_args()
    archive = checked_archive()
    source_root = ROOT / ".deps/lwjgl-core-source"
    expected = source_root / f"lwjgl3-{REVISION}"
    patch = ROOT / "patches/lwjgl-core-horizon.patch"
    prepared_pin = {"source_archive_sha256": ARCHIVE_SHA256,
                    "horizon_patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest()}
    marker = source_root / ".prepared-pin.json"
    cached_pin = json.loads(marker.read_text()) if marker.is_file() else None
    if cached_pin != prepared_pin or not (expected / "modules/lwjgl/core/src/main/c/common_tools.c").is_file():
        with tempfile.TemporaryDirectory(prefix="lwjgl-core-source-stage-", dir=ROOT / ".deps") as staging_name:
            staging = pathlib.Path(staging_name)
            with tarfile.open(archive, "r:gz") as tf:
                tf.extractall(staging, filter="data")
            staged_source = staging / f"lwjgl3-{REVISION}"
            if not (staged_source / "modules/lwjgl/core/src/main/c/common_tools.c").is_file():
                raise RuntimeError("unexpected contents in pinned LWJGL source archive")
            subprocess.run(["patch", "--batch", "--fuzz=0", "-p1", "-i", str(patch)], cwd=staged_source, check=True)
            prepared = ROOT / ".deps/lwjgl-core-source-prepared"
            shutil.rmtree(prepared, ignore_errors=True)
            staged_metadata = staging / ".prepared-pin.json"
            staged_metadata.write_text(json.dumps(prepared_pin, sort_keys=True) + "\n")
            # Replace the prepared tree only after extraction and strict patch
            # application have both succeeded.
            shutil.move(str(staging), str(prepared))
            shutil.rmtree(source_root, ignore_errors=True)
            prepared.rename(source_root)
    build = ROOT / "build/lwjgl-core"
    if args.host:
        compile_mode("host", expected, build / "host")
    if args.cross or not args.host:
        compile_mode("cross", expected, build / "horizon")


if __name__ == "__main__":
    main()
