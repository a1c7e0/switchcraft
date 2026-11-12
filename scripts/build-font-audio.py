#!/usr/bin/env python3
"""Build real FreeType/OpenAL API maps and an SDL3-only Switch OpenAL Soft.

The devkitPro OpenAL archive is intentionally not linked: it contains SDL2
backend references which cannot be composed with this SDL3-only program.
"""
import argparse
import ctypes.util
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "dependencies.lock.json").read_text())
OPENAL_PIN = LOCK["openal_soft"]
VERSION = OPENAL_PIN["version"]
REVISION = OPENAL_PIN["source_revision"]
ARCHIVE_URL = OPENAL_PIN["source_url"]
ARCHIVE_SHA256 = OPENAL_PIN["source_archive_sha256"]
if (VERSION != "1.25.1" or VERSION not in ARCHIVE_URL
        or not re.fullmatch(r"[0-9a-f]{40}", REVISION)
        or not re.fullmatch(r"[0-9a-f]{64}", ARCHIVE_SHA256)):
    raise RuntimeError("dependencies.lock.json has an incoherent OpenAL Soft source pin")
SOURCE_ARCHIVE = ROOT / f".deps/openal-soft-{VERSION}.tar.gz"
SOURCE_ROOT = ROOT / ".deps/openal-soft-source"
SOURCE_DIR = SOURCE_ROOT / f"openal-soft-{VERSION}"
PATCH_MARKER = SOURCE_ROOT / ".switchcraft-prepared.json"
DEVKITPRO = Path(os.environ.get("DEVKITPRO", ROOT / ".toolchain/opt/devkitpro")).resolve()
os.environ.setdefault("DEVKITPRO", str(DEVKITPRO))
PORTLIBS = DEVKITPRO / "portlibs/switch"
SDL_BUILD = ROOT / "build/sdl3"
BUILD = ROOT / "build/font-audio"
HOST_OUT = BUILD / "host"
CROSS_OUT = BUILD / "horizon"
OPENAL_BUILD = BUILD / "openal-cross"
API_FILTERS = {
    "freetype": re.compile(r"^(?:FT_|FTC_|TT_)[A-Za-z0-9_]+$"),
    "openal": re.compile(r"^(?:al[A-Z]|alc[A-Z])[A-Za-z0-9_]*$"),
}
NULL_BACKEND_LINE = '    BackendInfo{"null"sv, NullBackendFactory::getFactory},\n'


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run_logged(command: list[str], log: Path, cwd: Path = ROOT) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w") as output:
        result = subprocess.run(command, cwd=cwd, stdout=output, stderr=subprocess.STDOUT)
    if result.returncode:
        tail = "\n".join(log.read_text(errors="replace").splitlines()[-60:])
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}\n{tail}")


def checked_source() -> Path:
    SOURCE_ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    if not SOURCE_ARCHIVE.is_file():
        partial = SOURCE_ARCHIVE.with_suffix(".partial")
        urllib.request.urlretrieve(ARCHIVE_URL, partial)
        if sha256(partial) != ARCHIVE_SHA256:
            partial.unlink(missing_ok=True)
            raise RuntimeError("OpenAL Soft source archive SHA-256 mismatch")
        partial.replace(SOURCE_ARCHIVE)
    if sha256(SOURCE_ARCHIVE) != ARCHIVE_SHA256:
        raise RuntimeError("Cached OpenAL Soft source archive SHA-256 mismatch")

    patch_digest = hashlib.sha256(NULL_BACKEND_LINE.encode()).hexdigest()
    expected = {"version": VERSION, "revision": REVISION,
                "archive_sha256": ARCHIVE_SHA256, "null_backend_patch": patch_digest}
    cached = json.loads(PATCH_MARKER.read_text()) if PATCH_MARKER.is_file() else None
    alc = SOURCE_DIR / "alc/alc.cpp"
    if cached != expected or not alc.is_file():
        with tempfile.TemporaryDirectory(prefix="openal-soft-stage-", dir=ROOT / ".deps") as temp_name:
            staging = Path(temp_name)
            with tarfile.open(SOURCE_ARCHIVE, "r:gz") as archive:
                archive.extractall(staging, filter="data")
            staged_source = staging / f"openal-soft-{VERSION}"
            staged_alc = staged_source / "alc/alc.cpp"
            source = staged_alc.read_text()
            if source.count(NULL_BACKEND_LINE) != 1:
                raise RuntimeError("Pinned OpenAL source changed: expected one null-backend registration")
            # Null output discards samples while reporting a valid ALC device.
            # Omitting its factory makes a failed SDL3 device open fail closed.
            staged_alc.write_text(source.replace(NULL_BACKEND_LINE, "", 1))
            prepared = ROOT / ".deps/openal-soft-prepared"
            if prepared.exists():
                shutil.rmtree(prepared)
            marker = staged_source.parent / PATCH_MARKER.name
            marker.write_text(json.dumps(expected, sort_keys=True) + "\n")
            shutil.move(str(staging), prepared)
            if SOURCE_ROOT.exists():
                shutil.rmtree(SOURCE_ROOT)
            prepared.rename(SOURCE_ROOT)
    if PATCH_MARKER.is_file() and json.loads(PATCH_MARKER.read_text()) != expected:
        raise RuntimeError("OpenAL source preparation marker mismatch")
    if NULL_BACKEND_LINE.strip() in alc.read_text():
        raise RuntimeError("Silent null output backend remains registered")
    return SOURCE_DIR


def nm_exports(nm: str, library: Path, module: str, dynamic: bool = False) -> list[str]:
    command = [nm, "-g", "--defined-only"]
    if dynamic:
        command.insert(1, "-D")
    output = subprocess.check_output([*command, str(library)], text=True, errors="replace")
    names: set[str] = set()
    pattern = API_FILTERS[module]
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 2 or fields[-2] not in {"T", "W"}:
            continue
        name = fields[-1].split("@", 1)[0]
        if pattern.fullmatch(name):
            names.add(name)
    return sorted(names)


def write_export_include(path: Path, exports: dict[str, list[str]]) -> None:
    lines = ["/* Generated from actual nm T/W definitions by build-font-audio.py. */",
             "struct sc_font_audio_export { const char *name; void (*address)(void); };"]
    for module in ("freetype", "openal"):
        for name in exports[module]:
            lines.append(f"extern void {name}(void);")
        array = "sc_freetype_exports" if module == "freetype" else "sc_openal_exports"
        lines.append(f"static const struct sc_font_audio_export {array}[] = {{")
        lines.extend(f'    {{"{name}", (void (*)(void)){name}}},' for name in exports[module])
        lines.append("};")
    lines.append("")
    path.write_text("\n".join(lines))


def compile_resolver(cc: str, ar: str, include: Path, out: Path, host: bool = False) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    obj = out / "font_audio_resolver.o"
    flags = ["-std=c11", "-O2", "-ffunction-sections", "-fdata-sections"]
    if host:
        flags += ["-fPIC"]
    else:
        flags += ["-march=armv8-a+crc+crypto", "-mtune=cortex-a57", "-mtp=soft",
                  "-mno-outline-atomics", "-fPIE", "-D__SWITCH__"]
    subprocess.run([cc, *flags, "-I", str(ROOT / "include"), "-I", str(include),
                    "-c", str(ROOT / "src/font_audio_resolver.c"), "-o", str(obj)], check=True)
    if host:
        return obj
    archive = out / "libswitchcraft-font-audio.a"
    subprocess.run([ar, "rcs", str(archive), str(obj)], check=True)
    return archive


def package_metadata() -> dict:
    local = DEVKITPRO / "pacman/var/lib/pacman/local"
    result = {}
    for package in ("switch-freetype", "switch-harfbuzz", "switch-libpng", "switch-zlib", "switch-openal-soft"):
        records = sorted(local.glob(package + "-*"))
        if not records:
            continue
        fields = {}
        for line in (records[-1] / "desc").read_text(errors="replace").splitlines():
            if line.startswith("%") and line.endswith("%"):
                key = line.strip("%")
                fields[key] = []
            elif fields and line and not line.startswith("%"):
                fields[key].append(line)
        result[package] = {key.lower(): values[0] for key, values in fields.items() if values}
    return result


def find_host_library(name: str) -> Path | None:
    soname = ctypes.util.find_library(name)
    if not soname:
        return None
    ldconfig = shutil.which("ldconfig")
    if ldconfig:
        for line in subprocess.check_output([ldconfig, "-p"], text=True).splitlines():
            if soname in line and "=>" in line:
                candidate = Path(line.rsplit("=>", 1)[1].strip())
                if candidate.is_file():
                    return candidate
    for directory in (Path("/lib"), Path("/usr/lib"), Path("/lib64"), Path("/usr/lib64")):
        candidate = directory / soname
        if candidate.is_file():
            return candidate
    return None


def build_host() -> dict:
    nm, cc = shutil.which("nm"), shutil.which("cc")
    if not nm or not cc:
        raise RuntimeError("Host cc and nm are required for the host reference build")
    freetype = find_host_library("freetype")
    openal = find_host_library("openal")
    if not freetype or not openal:
        raise RuntimeError("Host FreeType/OpenAL runtime libraries are required for host reference tests")
    out = HOST_OUT
    out.mkdir(parents=True, exist_ok=True)
    exports = {"freetype": nm_exports(nm, freetype, "freetype", True),
               "openal": nm_exports(nm, openal, "openal", True)}
    if len(exports["freetype"]) < 150 or len(exports["openal"]) < 150:
        raise RuntimeError("Host dynamic libraries expose fewer procedures than expected")
    include = out / "font_audio_exports.inc"
    write_export_include(include, exports)
    obj = compile_resolver(cc, "", out, out, host=True)
    library = out / "libswitchcraft-font-audio.so"
    subprocess.run([cc, "-shared", "-Wl,--no-undefined", str(obj),
                    str(freetype), str(openal), "-o", str(library)], check=True)
    proof = {"freetype_exports": len(exports["freetype"]), "openal_exports": len(exports["openal"]),
             "freetype_library": str(freetype), "openal_library": str(openal),
             "provider_sha256": sha256(library), "host_execution": "not run by builder; see tests/test_font_audio.py"}
    (out / "build.json").write_text(json.dumps(proof, indent=2) + "\n")
    return proof


def build_cross(source: Path) -> dict:
    if not (SDL_BUILD / "SDL3Config.cmake").is_file() or not (SDL_BUILD / "libSDL3.a").is_file():
        raise RuntimeError("Build the Switch SDL3 target first; it is the real audren audio backend")
    cmake = ROOT / ".deps/host-cmake/cmake/data/bin/cmake"
    gcc = DEVKITPRO / "devkitA64/bin/aarch64-none-elf-gcc"
    gxx = DEVKITPRO / "devkitA64/bin/aarch64-none-elf-g++"
    nm = DEVKITPRO / "devkitA64/bin/aarch64-none-elf-nm"
    ar = DEVKITPRO / "devkitA64/bin/aarch64-none-elf-ar"
    if not cmake.is_file() or not all(path.is_file() for path in (gcc, gxx, nm, ar)):
        raise RuntimeError("Pinned CMake and AArch64 devkitPro toolchain are required")
    if not (DEVKITPRO / "libnx/lib/libnx.a").is_file():
        raise RuntimeError("libnx archive missing; cannot link the Horizon proof ELF")
    BUILD.mkdir(parents=True, exist_ok=True)
    cache = OPENAL_BUILD / "CMakeCache.txt"
    if cache.is_file():
        match = re.search(r"^CMAKE_HOME_DIRECTORY:INTERNAL=(.*)$", cache.read_text(errors="replace"), re.M)
        if match is None or Path(match.group(1)).resolve() != source.resolve():
            shutil.rmtree(OPENAL_BUILD)
    configure = [str(cmake), "-S", str(source), "-B", str(OPENAL_BUILD), "-G", "Unix Makefiles",
                 "-DCMAKE_TOOLCHAIN_FILE=" + str(DEVKITPRO / "cmake/Switch.cmake"),
                 "-DCMAKE_MODULE_PATH=" + str(DEVKITPRO / "cmake"),
                 "-DCMAKE_PREFIX_PATH=" + str(SDL_BUILD), "-DSDL3_DIR=" + str(SDL_BUILD),
                 "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_C_FLAGS_RELEASE=-O2 -DNDEBUG -g0",
                 "-DCMAKE_CXX_FLAGS_RELEASE=-O2 -DNDEBUG -g0", "-DLIBTYPE=STATIC",
                 "-DALSOFT_UTILS=OFF", "-DALSOFT_NO_CONFIG_UTIL=ON", "-DALSOFT_EXAMPLES=OFF",
                 "-DALSOFT_TESTS=OFF", "-DALSOFT_INSTALL=OFF", "-DALSOFT_INSTALL_CONFIG=OFF",
                 "-DALSOFT_INSTALL_HRTF_DATA=OFF", "-DALSOFT_INSTALL_AMBDEC_PRESETS=OFF",
                 "-DALSOFT_INSTALL_EXAMPLES=OFF", "-DALSOFT_INSTALL_UTILS=OFF",
                 "-DALSOFT_UPDATE_BUILD_VERSION=OFF", "-DALSOFT_ENABLE_MODULES=OFF",
                 "-DALSOFT_BACKEND_SDL3=ON", "-DALSOFT_REQUIRE_SDL3=ON",
                 "-DALSOFT_BACKEND_SDL2=OFF", "-DALSOFT_REQUIRE_SDL2=OFF",
                 "-DALSOFT_BACKEND_WAVE=OFF", "-DALSOFT_BACKEND_OSS=OFF",
                 "-DALSOFT_BACKEND_ALSA=OFF", "-DALSOFT_BACKEND_PULSEAUDIO=OFF",
                 "-DALSOFT_BACKEND_PIPEWIRE=OFF", "-DALSOFT_BACKEND_JACK=OFF",
                 "-DALSOFT_BACKEND_SNDIO=OFF", "-DALSOFT_BACKEND_PORTAUDIO=OFF",
                 "-DALSOFT_BACKEND_COREAUDIO=OFF", "-DALSOFT_BACKEND_SOLARIS=OFF",
                 "-DALSOFT_EMBED_HRTF_DATA=OFF"]
    run_logged(configure, BUILD / "cmake-configure.log")
    run_logged([str(cmake), "--build", str(OPENAL_BUILD), "--target", "OpenAL", "--parallel", "2"],
               BUILD / "openal-build.log")

    config = OPENAL_BUILD / "config_backends.h"
    config_text = config.read_text()
    if "#define HAVE_SDL3 1" not in config_text or "#define HAVE_SDL2 0" not in config_text:
        raise RuntimeError("Cross-built OpenAL is not configured for SDL3-only audio")
    openal_archive = OPENAL_BUILD / "libopenal.a"
    if not openal_archive.is_file():
        raise RuntimeError("OpenAL Soft SDL3 static archive missing")
    members = subprocess.check_output([str(ar), "t", str(openal_archive)], text=True).splitlines()
    if not any("sdl3" in name.lower() for name in members) or any("sdl2" in name.lower() for name in members):
        raise RuntimeError("OpenAL archive must contain the SDL3 backend and exclude SDL2")
    exports = {"freetype": nm_exports(str(nm), PORTLIBS / "lib/libfreetype.a", "freetype"),
               "openal": nm_exports(str(nm), openal_archive, "openal")}
    if len(exports["freetype"]) < 150 or len(exports["openal"]) < 150:
        raise RuntimeError("Target archives expose fewer public procedures than expected")
    out = CROSS_OUT
    out.mkdir(parents=True, exist_ok=True)
    include = out / "font_audio_exports.inc"
    write_export_include(include, exports)
    provider = compile_resolver(str(gcc), str(ar), out, out)

    probe_source = out / "font_audio_link_probe.c"
    probe_source.write_text(
        '#include "switchcraft/font_audio.h"\n'
        'int main(void) {\n'
        '  return !(sc_font_audio_available("freetype") && sc_font_audio_available("openal") &&\n'
        '           sc_font_audio_lookup("freetype", "FT_Init_FreeType") &&\n'
        '           sc_font_audio_lookup("openal", "alcOpenDevice") &&\n'
        '           sc_font_audio_export_count("freetype") && sc_font_audio_export_count("openal"));\n'
        '}\n')
    probe_obj = out / "font_audio_link_probe.o"
    arch = ["-march=armv8-a+crc+crypto", "-mtune=cortex-a57", "-mtp=soft", "-fPIE",
            "-ffunction-sections", "-fdata-sections", "-D__SWITCH__", "-O2", "-g0"]
    subprocess.run([str(gcc), *arch, "-I", str(ROOT / "include"), "-c", str(probe_source),
                    "-o", str(probe_obj)], check=True)
    proof = out / "font-audio-link-proof.elf"
    link_map = out / "font-audio-link-proof.map"
    libdir = DEVKITPRO / "portlibs/switch/lib"
    static_inputs = [openal_archive, PORTLIBS / "lib/libfreetype.a", SDL_BUILD / "libSDL3.a",
                     libdir / "libharfbuzz.a", libdir / "libpng16.a", libdir / "libz.a",
                     libdir / "libbz2.a", ROOT / ".deps/nvk/lib/libvulkan.a"]
    if any(not path.exists() for path in static_inputs):
        missing = [str(path) for path in static_inputs if not path.exists()]
        raise RuntimeError("Missing static link inputs: " + ", ".join(missing))
    link_cmd = [str(gxx), *arch, "-specs=" + str(DEVKITPRO / "libnx/switch.specs"),
                "-Wl,--gc-sections", "-Wl,--no-undefined", "-Wl,-Map=" + str(link_map),
                str(probe_obj), str(provider), "-Wl,--start-group", *map(str, static_inputs),
                str(DEVKITPRO / "libnx/lib/libnx.a"), "-lm", "-pthread", "-Wl,--end-group", "-o", str(proof)]
    subprocess.run(link_cmd, check=True, cwd=ROOT)
    undefined = subprocess.check_output([str(nm), "-u", str(proof)], text=True).strip()
    if undefined:
        raise RuntimeError("Cross-link proof has unresolved symbols:\n" + undefined[:4000])
    map_text = link_map.read_text(errors="replace")
    if ("libsysbase.a(libsysbase_libsysbase_a-pthread.o)" not in map_text
            or "pthread_create" not in map_text
            or "libnx.a(newlib.o)" not in map_text
            or "__syscall_thread_create" not in map_text):
        raise RuntimeError("OpenAL thread symbols did not resolve through libsysbase and libnx")
    if "libpthread.a(" in map_text:
        raise RuntimeError("Unexpected empty libpthread archive selected for OpenAL")
    if "SDL_GetAudioPlaybackDevices" not in map_text or "SDL_OpenAudioDevice" not in map_text:
        raise RuntimeError("SDL3 audio device procedures were not pulled into the proof link")

    metadata = {
        "openal_soft_version": VERSION, "openal_soft_tag_commit": REVISION,
        "openal_soft_source_archive_sha256": ARCHIVE_SHA256,
        "openal_soft_null_backend": "removed; unavailable audio device fails closed",
        "openal_soft_null_registration_patch_sha256": hashlib.sha256(NULL_BACKEND_LINE.encode()).hexdigest(),
        "openal_soft_backends": ["SDL3"], "sdl2_backend": False,
        "switch_sdl3_version": (ROOT / "build/sdl3/sdl3.pc").read_text().split("Version:", 1)[1].splitlines()[0].strip(),
        "portlibs_packages": package_metadata(),
        "freetype_exports": len(exports["freetype"]), "openal_exports": len(exports["openal"]),
        "freetype_archive_sha256": sha256(PORTLIBS / "lib/libfreetype.a"),
        "openal_archive_sha256": sha256(openal_archive),
        "provider_archive_sha256": sha256(out / "libswitchcraft-font-audio.a"),
        "link_proof_elf_sha256": sha256(proof), "unresolved_symbols": 0,
        "openal_thread_resolution": "libsysbase pthread implementation backed by libnx __syscall_thread_create",
        "openal_device_execution": "NOT TESTED ON HORIZON",
        "silent_null_backend": False,
    }
    (out / "font-audio-build.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", action="store_true", help="build host reference provider from system libraries")
    parser.add_argument("--cross", action="store_true", help="build SDL3-only Switch OpenAL and link proof")
    args = parser.parse_args()
    if not args.host and not args.cross:
        args.cross = True
    source = checked_source() if args.cross else None
    results = {}
    if args.host:
        results["host"] = build_host()
    if args.cross:
        assert source is not None
        results["horizon"] = build_cross(source)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
