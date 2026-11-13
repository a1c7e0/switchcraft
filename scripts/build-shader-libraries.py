#!/usr/bin/env python3
"""Build pinned Shaderc + SPIRV-Cross C API archives for host/Horizon."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import shlex
import subprocess
import tarfile
import tempfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "dependencies.lock.json").read_text())
PINS = LOCK.get("shader_libraries")
EXPECTED = {"shaderc", "glslang", "spirv_headers", "spirv_tools", "spirv_cross"}
if not isinstance(PINS, dict) or set(PINS) != EXPECTED:
    raise RuntimeError("dependencies.lock.json needs shader_libraries pins for " + ", ".join(sorted(EXPECTED)))
if PINS["shaderc"].get("version") != "2026.3" or PINS["spirv_cross"].get("version") != "0.68.0":
    raise RuntimeError("shader_libraries versions must match LWJGL 3.4.3: Shaderc 2026.3 / SPIRV-Cross 0.68.0")


def verify_pin(name: str, entry: dict) -> tuple[str, str, str]:
    rev, url, digest = (entry.get(k) for k in ("source_revision", "source_url", "source_archive_sha256"))
    if not isinstance(rev, str) or not re.fullmatch(r"[0-9a-f]{40}", rev):
        raise RuntimeError(f"shader_libraries.{name}.source_revision must be an immutable commit SHA")
    if not isinstance(url, str) or rev not in url:
        raise RuntimeError(f"shader_libraries.{name}.source_url must include its immutable commit SHA")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise RuntimeError(f"shader_libraries.{name}.source_archive_sha256 must be SHA-256")
    return rev, url, digest


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def source(name: str) -> pathlib.Path:
    rev, url, digest = verify_pin(name, PINS[name])
    cache = ROOT / ".deps/shader-libraries"
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / f"{name}-{rev}.tar.gz"
    if not archive.exists():
        partial = archive.with_suffix(".partial")
        urllib.request.urlretrieve(url, partial)
        if sha256(partial) != digest:
            partial.unlink(missing_ok=True)
            raise RuntimeError(f"{name}: downloaded source archive hash mismatch")
        partial.replace(archive)
    if sha256(archive) != digest:
        raise RuntimeError(f"{name}: cached source archive hash mismatch")
    source_root = pathlib.Path(os.environ.get("SWITCHCRAFT_SHADER_SOURCE_DIR", cache / "sources"))
    source_root.mkdir(parents=True, exist_ok=True)
    dest = source_root / f"{name}-{rev}"
    marker = dest / ".source-pin.json"
    if not marker.is_file() or json.loads(marker.read_text()) != {"revision": rev, "sha256": digest}:
        with tempfile.TemporaryDirectory(prefix=f"{name}-stage-", dir=source_root) as td:
            stage = pathlib.Path(td)
            with tarfile.open(archive, "r:gz") as tf:
                tf.extractall(stage, filter="data")
            roots = [p for p in stage.iterdir() if p.is_dir()]
            if len(roots) != 1:
                raise RuntimeError(f"{name}: unexpected source archive layout")
            roots[0].rename(stage / "source")
            (stage / "source/.source-pin.json").write_text(json.dumps({"revision": rev, "sha256": digest}, sort_keys=True) + "\n")
            shutil.rmtree(dest, ignore_errors=True)
            (stage / "source").rename(dest)
    return dest


def cmake_path() -> str:
    candidates = [ROOT / ".deps/host-cmake/cmake/data/bin/cmake", pathlib.Path(shutil.which("cmake") or "")]
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    raise RuntimeError("host CMake not found")


def prepare_sources() -> tuple[pathlib.Path, pathlib.Path]:
    shaderc = source("shaderc")
    patch = ROOT / "patches/shader-libraries-horizon.patch"
    patch_hash = sha256(patch)
    patch_marker = shaderc / ".horizon-patch.json"
    patch_pin = {"sha256": patch_hash}
    if patch_marker.is_file() and json.loads(patch_marker.read_text()) != patch_pin:
        shutil.rmtree(shaderc)
        shaderc = source("shaderc")
        patch_marker = shaderc / ".horizon-patch.json"
    if not patch_marker.is_file():
        subprocess.run(["patch", "--batch", "--fuzz=0", "-p1", "-i", str(patch)], cwd=shaderc, check=True)
        patch_marker.write_text(json.dumps(patch_pin, sort_keys=True) + "\n")
    glslang = source("glslang")
    headers = source("spirv_headers")
    tools = source("spirv_tools")
    spvc = source("spirv_cross")
    # Shaderc's upstream CMake expects its DEPS checkout layout. Symlinks keep
    # the immutable source trees single-copy and are recreated on each build.
    third = shaderc / "third_party"
    third.mkdir(exist_ok=True)
    for path, target in ((third / "glslang", glslang), (third / "spirv-tools", tools)):
        if path.is_symlink() or path.exists():
            if path.is_symlink() and path.resolve() == target.resolve():
                continue
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
        path.symlink_to(target, target_is_directory=True)
    external = tools / "external"
    external.mkdir(exist_ok=True)
    hpath = external / "spirv-headers"
    if hpath.is_symlink() or hpath.exists():
        if hpath.is_symlink() and hpath.resolve() == headers.resolve():
            pass
        else:
            shutil.rmtree(hpath) if hpath.is_dir() and not hpath.is_symlink() else hpath.unlink()
            hpath.symlink_to(headers, target_is_directory=True)
    else:
        hpath.symlink_to(headers, target_is_directory=True)
    return shaderc, spvc



def retain_licenses() -> None:
    sources = {name: source(name) for name in EXPECTED}
    candidates = {
        "shaderc": ("LICENSE", "shaderc"),
        "glslang": ("LICENSE.txt", "glslang"),
        "spirv_headers": ("LICENSE", "spirv-headers"),
        "spirv_tools": ("LICENSE", "spirv-tools"),
        "spirv_cross": ("LICENSE", "spirv-cross"),
    }
    out = ROOT / "licenses/native-shaders"
    out.mkdir(parents=True, exist_ok=True)
    for name, (filename, label) in candidates.items():
        license_path = sources[name] / filename
        if not license_path.is_file():
            raise RuntimeError(f"{name}: upstream license file missing at {license_path}")
        shutil.copyfile(license_path, out / f"LICENSE.{label}")


def configure_build(mode: str, shaderc_src: pathlib.Path, spvc_src: pathlib.Path, build: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    cmake = cmake_path()
    build.mkdir(parents=True, exist_ok=True)
    cross = mode == "horizon"
    # Archive extractions have no .git metadata. Do not let upstream version
    # probes climb into Switchcraft's unrelated checkout and stamp that commit
    # into generated headers. Preserve any caller-provided ceilings.
    ceilings = [str(ROOT.resolve())]
    ceilings.extend(path for path in os.environ.get("GIT_CEILING_DIRECTORIES", "").split(os.pathsep) if path)
    for source_tree in (shaderc_src, spvc_src):
        parent = str(source_tree.resolve().parent)
        if parent not in ceilings:
            ceilings.append(parent)
    os.environ["GIT_CEILING_DIRECTORIES"] = os.pathsep.join(ceilings)
    # Keep generated timestamps stable; source identity comes from the pinned
    # revisions and archive hashes, not from a machine's current clock.
    os.environ.setdefault("SOURCE_DATE_EPOCH", "0")
    devkit = pathlib.Path(os.environ.get("DEVKITPRO", ROOT / ".toolchain/opt/devkitpro"))
    if cross:
        # libnx's switch.specs and sysbase need this even when DEVKITPRO was
        # not exported by the caller and we found the toolchain via ROOT.
        os.environ.setdefault("DEVKITPRO", str(devkit))
    cc = shutil.which("cc") if not cross else str(devkit / "devkitA64/bin/aarch64-none-elf-gcc")
    cxx = shutil.which("c++") if not cross else str(devkit / "devkitA64/bin/aarch64-none-elf-g++")
    ar = shutil.which("ar") if not cross else str(devkit / "devkitA64/bin/aarch64-none-elf-ar")
    nm = shutil.which("nm") if not cross else str(devkit / "devkitA64/bin/aarch64-none-elf-nm")
    if not all(x and pathlib.Path(x).is_file() for x in (cc, cxx, ar, nm)):
        raise RuntimeError(f"{mode}: required compilers/ar/nm were not found")
    defines = ["-Os", "-g0", "-ffunction-sections", "-fdata-sections"]
    if cross:
        libnx = devkit / "libnx/include"
        if not libnx.is_dir():
            raise RuntimeError(f"Horizon libnx headers missing: {libnx}")
        defines += ["-march=armv8-a+crc+crypto", "-mtune=cortex-a57", "-mtp=soft", "-mno-outline-atomics", "-fPIE", "-D__SWITCH__", "-DLWJGL_HORIZON_SHADERC", f"-I{libnx}"]
    base = [cmake, "-S", str(shaderc_src), "-B", str(build / "shaderc"),
            "-DCMAKE_BUILD_TYPE=MinSizeRel", f"-DCMAKE_C_COMPILER={cc}", f"-DCMAKE_CXX_COMPILER={cxx}", f"-DCMAKE_AR={ar}",
            "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
            "-DBUILD_SHARED_LIBS=OFF", "-DSHADERC_SKIP_TESTS=ON", "-DSHADERC_SKIP_EXAMPLES=ON",
            "-DSHADERC_ENABLE_WGSL_OUTPUT=OFF", "-DSHADERC_ENABLE_INSTALL=OFF",
            "-DSPIRV_SKIP_TESTS=ON", "-DSPIRV_SKIP_EXECUTABLES=ON", "-DENABLE_GLSLANG_BINARIES=OFF",
            "-DENABLE_HLSL=ON", "-DENABLE_OPT=ON", f"-DCMAKE_C_FLAGS={' '.join(defines)}",
            f"-DCMAKE_CXX_FLAGS={' '.join(defines)}"]
    if cross:
        base += ["-DCMAKE_SYSTEM_NAME=Generic", "-DCMAKE_SYSTEM_PROCESSOR=aarch64", "-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY"]
    subprocess.run(base, check=True)
    subprocess.run([cmake, "--build", str(build / "shaderc"), "--target", "shaderc_combined", "-j2"], check=True)
    cross_args = [cmake, "-S", str(spvc_src), "-B", str(build / "spirv-cross"),
                  "-DCMAKE_BUILD_TYPE=MinSizeRel", f"-DCMAKE_C_COMPILER={cc}", f"-DCMAKE_CXX_COMPILER={cxx}", f"-DCMAKE_AR={ar}",
                  "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
                  "-DSPIRV_CROSS_CLI=OFF", "-DSPIRV_CROSS_ENABLE_TESTS=OFF", "-DSPIRV_CROSS_ENABLE_MSL=ON",
                  "-DSPIRV_CROSS_ENABLE_HLSL=ON", "-DSPIRV_CROSS_ENABLE_CPP=ON", "-DSPIRV_CROSS_ENABLE_REFLECT=ON",
                  "-DCMAKE_DISABLE_FIND_PACKAGE_Git=ON",
                  "-DBUILD_SHARED_LIBS=OFF", f"-DCMAKE_C_FLAGS={' '.join(defines)}", f"-DCMAKE_CXX_FLAGS={' '.join(defines)}"]
    if cross:
        cross_args += ["-DCMAKE_SYSTEM_NAME=Generic", "-DCMAKE_SYSTEM_PROCESSOR=aarch64", "-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY"]
    subprocess.run(cross_args, check=True)
    subprocess.run([cmake, "--build", str(build / "spirv-cross"), "--target", "spirv-cross-c", "-j2"], check=True)
    return build, pathlib.Path(nm)



def archive_for(build: pathlib.Path, pattern: str) -> pathlib.Path:
    found = sorted(build.rglob(pattern))
    if len(found) != 1:
        raise RuntimeError(f"expected one {pattern} below {build}, found {len(found)}")
    return found[0]


def symbols(nm: pathlib.Path, archive: pathlib.Path, prefix: str) -> list[str]:
    out = subprocess.check_output([str(nm), "-g", "--defined-only", str(archive)], text=True)
    names = set()
    for line in out.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[-2] in ("T", "W") and fields[-1].startswith(prefix):
            names.add(fields[-1])
    return sorted(names)


def expected_api(module: pathlib.Path, cls: str, prefix: str) -> set[str]:
    java = next(module.rglob(f"{cls}.java"))
    return set(re.findall(r'apiGetFunctionAddress\([^,]+,\s*"(' + re.escape(prefix) + r'[A-Za-z0-9_]+)"\)', java.read_text()))


def generate_exports(build: pathlib.Path, nm: pathlib.Path) -> None:
    shaderc_archive = archive_for(build / "shaderc", "libshaderc_combined.a")
    spvc_build = build / "spirv-cross"
    spvc_archives = [archive_for(spvc_build, name) for name in (
        "libspirv-cross-c.a", "libspirv-cross-core.a", "libspirv-cross-glsl.a",
        "libspirv-cross-hlsl.a", "libspirv-cross-msl.a", "libspirv-cross-cpp.a",
        "libspirv-cross-reflect.a")]
    spvc_archive = spvc_archives[0]
    shaderc = symbols(nm, shaderc_archive, "shaderc_")
    spvc = symbols(nm, spvc_archive, "spvc_")
    source = ROOT / ".deps/lwjgl-core-source/lwjgl3-30fac9b95f99cda97312232be25ba55297bf9951/modules/lwjgl"
    required_shaderc = expected_api(source / "shaderc", "Shaderc", "shaderc_")
    required_spvc = expected_api(source / "spvc", "Spvc", "spvc_")
    missing = sorted((required_shaderc - set(shaderc)) | (required_spvc - set(spvc)))
    if missing:
        raise RuntimeError("linked archives omit LWJGL 3.4.3 C API exports: " + ", ".join(missing))
    # Collect all current C API T/W exports, while asserting every exact
    # function pointer used by pinned LWJGL is present in the actual archive.
    inc = build / "shader_libraries_exports.inc"
    rows = ["/* generated from compiled pinned upstream archives using nm */",
            "struct sc_shader_library_export { const char *name; void (*address)(void); };"]
    for name in shaderc + spvc:
        rows.append(f"extern void {name}(void);")
    for table, names in (("sc_shaderc_exports", shaderc), ("sc_spvc_exports", spvc)):
        rows.append(f"static const struct sc_shader_library_export {table}[] = {{")
        rows.extend(f'    {{"{name}", (void (*)(void)){name}}},' for name in names)
        rows.append("};")
    inc.write_text("\n".join(rows) + "\n")
    flags = ["-Os", "-g0", "-ffunction-sections", "-fdata-sections"]
    if build.name == "horizon":
        devkit = pathlib.Path(os.environ.get("DEVKITPRO", ROOT / ".toolchain/opt/devkitpro"))
        cc = devkit / "devkitA64/bin/aarch64-none-elf-gcc"
        flags += ["-march=armv8-a+crc+crypto", "-mtune=cortex-a57", "-mtp=soft", "-mno-outline-atomics", "-fPIE", "-D__SWITCH__"]
        ar = devkit / "devkitA64/bin/aarch64-none-elf-ar"
    else:
        cc = pathlib.Path(shutil.which("cc") or "cc")
        ar = pathlib.Path(shutil.which("ar") or "ar")
    resolver = build / "shader_libraries_resolver.o"
    subprocess.run([str(cc), "-std=c11", *flags, "-I", str(ROOT / "include"), "-I", str(build),
                    "-c", str(ROOT / "src/shader_libraries_resolver.c"), "-o", str(resolver)], check=True)
    provider_objects = [resolver]
    subprocess.run([str(ar), "rcs", str(build / "libswitchcraft-shader-libraries-provider.a"), *(str(x) for x in provider_objects)], check=True)
    # Retain an archive-level proof for inspection, then make a real target ELF
    # link so pthread references resolve through devkitPro's real sysbase.
    objects = build / "link-proof.o"
    subprocess.run([str(cc), "-r", *(str(x) for x in provider_objects), "-Wl,--whole-archive", str(shaderc_archive),
                    *(str(x) for x in spvc_archives), "-Wl,--no-whole-archive", "-o", str(objects)], check=True)
    if build.name == "horizon":
        devkit = pathlib.Path(os.environ.get("DEVKITPRO", ROOT / ".toolchain/opt/devkitpro"))
        gcc = devkit / "devkitA64/bin/aarch64-none-elf-gcc"
        gxx = devkit / "devkitA64/bin/aarch64-none-elf-g++"
        probe_c = build / "shader_libraries_link_probe.c"
        probe_c.write_text(
            '#include "switchcraft/shader_libraries.h"\n'
            'int main(void) { return !(sc_shader_libraries_available("shaderc") && '
            'sc_shader_libraries_lookup("shaderc", "shaderc_compiler_initialize") && '
            'sc_shader_libraries_lookup("spirv-cross-c", "spvc_context_create")); }\n')
        probe_o = build / "shader_libraries_link_probe.o"
        subprocess.run([str(gcc), "-std=c11", *flags, "-I", str(ROOT / "include"), "-c", str(probe_c), "-o", str(probe_o)], check=True)
        proof_elf = build / "shader-libraries-link-proof.elf"
        proof_map = build / "shader-libraries-link-proof.map"
        libnx = devkit / "libnx/lib/libnx.a"
        link = [str(gxx), *flags, "-specs=" + str(devkit / "libnx/switch.specs"),
                "-Wl,--gc-sections", "-Wl,--no-undefined", "-Wl,-Map=" + str(proof_map), str(probe_o),
                *(str(x) for x in provider_objects), "-Wl,--start-group", str(shaderc_archive),
                *(str(x) for x in spvc_archives), str(libnx), "-lm", "-pthread", "-Wl,--end-group", "-o", str(proof_elf)]
        subprocess.run(link, check=True, cwd=ROOT)
        undefined = subprocess.check_output([str(nm), "-u", str(proof_elf)], text=True).strip()
        if undefined:
            raise RuntimeError("Horizon shader link proof has unresolved symbols:\n" + undefined[:4000])
        map_text = proof_map.read_text(errors="replace")
        required_link_evidence = (
            "libsysbase.a(libsysbase_libsysbase_a-pthread.o)", "pthread_mutex_lock",
            "libnx.a(newlib.o)", "__syscall_tls_get", "__aarch64_read_tp")
        absent = [evidence for evidence in required_link_evidence if evidence not in map_text]
        if absent:
            raise RuntimeError("Horizon shader link did not resolve through real libsysbase/libnx: " + ", ".join(absent))
        if "libpthread.a(" in map_text:
            raise RuntimeError("Unexpected empty libpthread archive selected for Horizon shaders")
        proof_log = build / "shader-libraries-link-proof.log"
        proof_log.write_text(
            "command: " + shlex.join(link) + "\n"
            + "undefined_symbols: none\n"
            + "required_map_evidence: " + ", ".join(required_link_evidence) + "\n"
            + "empty_libpthread_archive_selected: no\n"
        )
    print(f"{build.name}: {len(shaderc)} shaderc_* + {len(spvc)} spvc_* defined function symbols; all LWJGL API pointers resolve")


def run_host_smoke(build: pathlib.Path) -> None:
    cc = shutil.which("cc")
    cxx = shutil.which("c++")
    if not cc or not cxx:
        raise RuntimeError("host C/C++ compilers are required for host shader validation")
    shaderc_archive = archive_for(build / "shaderc", "libshaderc_combined.a")
    spvc_build = build / "spirv-cross"
    spvc_archives = [archive_for(spvc_build, name) for name in (
        "libspirv-cross-c.a", "libspirv-cross-core.a", "libspirv-cross-glsl.a",
        "libspirv-cross-hlsl.a", "libspirv-cross-msl.a", "libspirv-cross-cpp.a",
        "libspirv-cross-reflect.a")]
    shaderc_src = source("shaderc")
    spvc_src = source("spirv_cross")
    binary = build / "shader_libraries_smoke"
    subprocess.run([cc, "-std=c11", "-O2", "-I", str(ROOT / "include"),
                    "-I", str(shaderc_src / "libshaderc/include"), "-I", str(spvc_src),
                    str(ROOT / "tests/shader_libraries_smoke.c"),
                    str(build / "shader_libraries_resolver.o"), str(shaderc_archive),
                    "-Wl,--start-group", *(str(x) for x in spvc_archives), "-Wl,--end-group",
                    "-lstdc++", "-lm", "-pthread", "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
    print("host: real GLSL -> SPIR-V compilation and SPIRV-Cross stage-input reflection passed")

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", action="store_true", help="build host libraries and run real compile/reflection smoke test")
    ap.add_argument("--cross", action="store_true", help="build AArch64 Horizon archives (default)")
    args = ap.parse_args()
    host = args.host
    cross = args.cross or not host
    shaderc_src, spvc_src = prepare_sources()
    retain_licenses()
    build_root = pathlib.Path(os.environ.get("SWITCHCRAFT_SHADER_BUILD_DIR", ROOT / "build/shader-libraries"))
    if host:
        configure_build("host", shaderc_src, spvc_src, build_root / "host")
    if cross:
        configure_build("horizon", shaderc_src, spvc_src, build_root / "horizon")
    if host:
        generate_exports(build_root / "host", pathlib.Path(shutil.which("nm") or "nm"))
        run_host_smoke(build_root / "host")
    if cross:
        generate_exports(build_root / "horizon", pathlib.Path(os.environ.get("DEVKITPRO", ROOT / ".toolchain/opt/devkitpro")) / "devkitA64/bin/aarch64-none-elf-nm")
    print("shader libraries built with genuine upstream C APIs")


if __name__ == "__main__":
    main()
