#!/usr/bin/env python3
"""Compile pinned LWJGL STB and VMA native modules for host and Horizon."""
import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "dependencies.lock.json").read_text())
PIN = LOCK["lwjgl_core"]
REVISION = PIN["source_revision"]
SOURCE = ROOT / ".deps/lwjgl-core-source" / f"lwjgl3-{REVISION}"
ARCHIVE_PIN_FILE = ROOT / ".deps/lwjgl-core-source/.prepared-pin.json"


def verify_source() -> pathlib.Path:
    if not SOURCE.is_dir() or not ARCHIVE_PIN_FILE.is_file():
        raise RuntimeError("run the pinned LWJGL core source preparation/build first")
    prepared = json.loads(ARCHIVE_PIN_FILE.read_text())
    if prepared.get("source_archive_sha256") != PIN.get("source_archive_sha256"):
        raise RuntimeError("prepared LWJGL source cache does not match dependencies.lock.json")
    return SOURCE


def write_platform_header(path: pathlib.Path, host: bool) -> None:
    if host:
        path.write_text("""/* Host references use genuine Linux headers/configuration. */
#include <stdint.h>
#include \"LinuxConfig.h\"
""")
    else:
        path.write_text("""/* Horizon: warning controls only; no Linux OS emulation. */
#include <stdint.h>
#define DISABLE_WARNINGS() _Pragma(\"GCC diagnostic push\")
#define ENABLE_WARNINGS() _Pragma(\"GCC diagnostic pop\")
""")


def nm_exports(nm: str, objects: dict[str, list[pathlib.Path]]) -> dict[str, set[str]]:
    result = {"lwjgl_stb": set(), "lwjgl_vma": set()}
    for module, module_objects in objects.items():
        for obj in module_objects:
            lines = subprocess.check_output([nm, "-g", "--defined-only", str(obj)], text=True)
            for line in lines.splitlines():
                match = re.search(r"\s[TW]\s+((?:Java_[A-Za-z0-9_]+)|JNI_OnLoad_lwjgl_(?:stb|vma))$", line)
                if not match:
                    continue
                symbol = match.group(1)
                if symbol.startswith("JNI_OnLoad_"):
                    lifecycle_module = symbol.removeprefix("JNI_OnLoad_")
                    result[lifecycle_module].add(symbol)
                else:
                    result[module].add(symbol)
    return result


def build(mode: str) -> None:
    source = verify_source()
    modules = source / "modules/lwjgl"
    core_c = modules / "core/src/main/c"
    stb = modules / "stb"
    vma = modules / "vma"
    out = ROOT / "build/lwjgl-utilities" / mode
    out.mkdir(parents=True, exist_ok=True)
    compat = out / "lwjgl_utilities_config.h"
    host = mode == "host"
    write_platform_header(compat, host)

    if host:
        cc = shutil.which("cc")
        cxx = shutil.which("c++")
        ar = shutil.which("ar")
        nm = shutil.which("nm")
        jni = ROOT / ".deps/host-jdk25/jdk-25.0.5+8/include"
        jni_includes = [jni, jni / "linux"]
        common = ["-O2", "-fPIC", "-pthread", "-DLWJGL_LINUX"]
        cflags = ["-std=c11", *common]
        cxxflags = ["-std=c++17", *common]
        vkincludes = [ROOT / ".deps/vk-headers/include"]
    else:
        devkit = pathlib.Path(os.environ.get("DEVKITPRO", ROOT / ".toolchain/opt/devkitpro"))
        prefix = devkit / "devkitA64/bin/aarch64-none-elf-"
        cc, cxx, ar, nm = (str(prefix.with_name(prefix.name + tool)) for tool in ("gcc", "g++", "ar", "nm"))
        runtime_jni = ROOT / "build/java25-integrated/runtime/openjdk25-horizon-runtime/include"
        jni_includes = [runtime_jni, runtime_jni / "horizon"]
        common = ["-march=armv8-a+crc+crypto", "-mtune=cortex-a57", "-mtp=soft",
                  "-mno-outline-atomics", "-fPIE", "-ffunction-sections", "-fdata-sections",
                  "-D__SWITCH__", "-O2"]
        cflags = ["-std=c11", *common]
        cxxflags = ["-std=c++17", *common]
        vkincludes = [ROOT / ".deps/vk-headers/include"]
    if not all((cc, cxx, ar, nm)):
        raise RuntimeError(f"{mode} C/C++ toolchain is incomplete")

    include_dirs = [core_c, core_c / "linux", stb / "src/main/c", vma / "src/main/c", *jni_includes, *vkincludes]
    include_args = [arg for path in include_dirs for arg in ("-I", str(path))]
    lifecycle_common = """#include <jni.h>

static jint lwjgl_utilities_check_jni18(JavaVM *vm) {
    JNIEnv *env = NULL;
    if (vm == NULL || (*vm)->GetEnv(vm, (void **)&env, JNI_VERSION_1_8) != JNI_OK || env == NULL)
        return JNI_ERR;
    return JNI_VERSION_1_8;
}
"""
    lifecycle_sources = {}
    for module in ("lwjgl_stb", "lwjgl_vma"):
        lifecycle_source = out / f"{module}_lifecycle.c"
        lifecycle_source.write_text(lifecycle_common + f"""
JNIEXPORT jint JNICALL JNI_OnLoad_{module}(JavaVM *vm, void *reserved) {{
    (void)reserved;
    return lwjgl_utilities_check_jni18(vm);
}}
""")
        lifecycle_sources[module] = lifecycle_source

    module_objects: dict[str, list[pathlib.Path]] = {"lwjgl_stb": [], "lwjgl_vma": []}

    def compile_sources(module: str, files: list[pathlib.Path], compiler: str, flags: list[str]) -> None:
        for source_file in files:
            obj = out / f"{module}_{source_file.stem}.o"
            module_flags = []
            if module == "lwjgl_vma":
                # Upstream declares these module-local globals with external
                # linkage because desktop builds put each LWJGL module in a
                # separate DSO. A static NRO needs equivalent module isolation.
                module_flags = [f"-Dorg_lwjgl_{name}=org_lwjgl_vma_{name}"
                                for name in ("malloc", "calloc", "realloc", "free", "aligned_alloc", "aligned_free")]
            command = [compiler, *flags, *module_flags, "-include", str(compat), *include_args,
                       "-c", str(source_file), "-o", str(obj)]
            subprocess.run(command, check=True)
            module_objects[module].append(obj)

    stb_sources = sorted((stb / "src/generated/c").glob("*.c"))
    if not stb_sources:
        raise RuntimeError("pinned LWJGL source contains no generated STB JNI files")
    compile_sources("lwjgl_stb", stb_sources, cc, cflags)
    vma_sources = sorted((vma / "src/generated/c").glob("*.cpp"))
    if not vma_sources or len(vma_sources) != 2:
        raise RuntimeError("expected pinned LWJGL LibVma.cpp and Vma.cpp")
    compile_sources("lwjgl_vma", vma_sources, cxx, cxxflags)

    for module, lifecycle_source in lifecycle_sources.items():
        lifecycle_obj = out / f"{module}_lifecycle.o"
        subprocess.run([cc, "-std=c11", *common, *include_args, "-c", str(lifecycle_source), "-o", str(lifecycle_obj)], check=True)
        module_objects[module].append(lifecycle_obj)
    exports = nm_exports(nm, module_objects)
    expected_lifecycle = {"JNI_OnLoad_lwjgl_stb", "JNI_OnLoad_lwjgl_vma"}
    actual_lifecycle = {symbol for symbols in exports.values() for symbol in symbols if symbol.startswith("JNI_OnLoad_")}
    if actual_lifecycle != expected_lifecycle:
        raise RuntimeError(f"lifecycle export mismatch: {actual_lifecycle}")
    if not exports["lwjgl_stb"] or not exports["lwjgl_vma"]:
        raise RuntimeError("nm found no actual JNI exports for one of the utility modules")

    inc = out / "lwjgl_utilities_exports.inc"
    rows = ["/* Generated from nm -g --defined-only; Java methods and lifecycle hooks only. */",
            "struct sc_lwjgl_utilities_export { const char *module; const char *name; void (*address)(void); };"]
    rows.extend(f"extern void {symbol}(void);" for module in ("lwjgl_stb", "lwjgl_vma") for symbol in sorted(exports[module]))
    rows.append("static const struct sc_lwjgl_utilities_export sc_lwjgl_utilities_exports[] = {")
    for module in ("lwjgl_stb", "lwjgl_vma"):
        for symbol in sorted(exports[module]):
            rows.append(f'    {{"{module}", "{symbol}", (void (*)(void)){symbol}}},')
    rows.extend(["};", ""])
    inc.write_text("\n".join(rows))

    resolver_obj = out / "lwjgl_utilities_resolver.o"
    subprocess.run([cc, "-std=c11", *common, "-I", str(ROOT / "include"), "-I", str(out),
                    "-c", str(ROOT / "src/lwjgl_utilities_resolver.c"), "-o", str(resolver_obj)], check=True)
    archive = out / "liblwjgl-utilities.a"
    all_objects = list(dict.fromkeys([*module_objects["lwjgl_stb"], *module_objects["lwjgl_vma"], resolver_obj]))
    subprocess.run([ar, "rcs", str(archive), *(str(obj) for obj in all_objects)], check=True)
    proof = out / "lwjgl-utilities-link-proof.o"
    subprocess.run([cxx, "-r", *(str(obj) for obj in all_objects), "-o", str(proof)], check=True)
    if host:
        for module in ("lwjgl_stb", "lwjgl_vma"):
            subprocess.run([cxx, "-shared", *(str(obj) for obj in module_objects[module]),
                            "-lm", "-o", str(out / f"lib{module}.so")], check=True)
    inventory = {module: sorted(exports[module]) for module in exports}
    (out / "jni-exports.json").write_text(json.dumps(inventory, indent=2) + "\n")
    print(f"{mode}: {len(exports['lwjgl_stb'])-1} STB Java JNI + 1 STB lifecycle; "
          f"{len(exports['lwjgl_vma'])-1} VMA Java JNI + 1 VMA lifecycle -> {archive}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", action="store_true", help="build host reference module libraries")
    parser.add_argument("--cross", action="store_true", help="build Horizon AArch64 static provider")
    args = parser.parse_args()
    if not args.host and not args.cross:
        args.cross = True
    if args.host:
        build("host")
    if args.cross:
        build("horizon")


if __name__ == "__main__":
    main()
