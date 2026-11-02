# Building Switchcraft

## Reproduced environment

The initial repository was empty. The build ran on Linux x86_64 with host
GCC/G++, Python 3.12, GNU Make and Git, with no Switch hardware attached.
The cloud executor provides 7.9 GB root disk and about 9.7 GiB RAM.

| Component | Pinned version |
| --- | --- |
| devkitPro image | `devkitpro/devkita64@sha256:1fc388c3a0d34bd2045a6dadcb1020e069d5f876a187fd705de14b4440c00282` |
| devkitA64 GCC | 15.2.0, package `15.2.0-7` |
| Binutils | `2.45.1-2` |
| Newlib | `4.6.0.20260123-4` |
| libnx | `4.12.0-1` |
| Mesa OpenGL | devkitPro `switch-mesa-20.1.0-5` |
| GLAD | `0.1.27-1` |
| Mesa NVK | `nvk-switch-mesa-25.0.7-r1`, archive and static library SHA-256 in the lock file |
| Vulkan headers | `v1.4.305`; fills omitted `vk_video/` headers in the NVK release |
| miniJVM | `87c9808145fabbf13c7a0d6b6d1e5bfbdbdba5a8`, local patch in `patches/` |
| Host JDK | Temurin `8u504-b01`; used to compile class libraries/tests, never shipped as a Switch runtime |
| nlohmann JSON | `3.11.3`, vendored single header and MIT notice |
| Shader generator | glslangValidator `12.0.0`; generated SPIR-V arrays are checked in |

`dependencies.lock.json` fixes URLs and SHA-256 hashes. Bootstrap checks image
index, amd64 manifest and every layer digest. Toolchain/package inventory is
included in the release manifest.

## One-command native host build

```sh
bash scripts/build-all.sh
```

The pipeline executes dependency verification, cross-builds, interpreter and
metadata host tests, artifact checks, packaging and checksum/ZIP verification.
It does not execute NROs on the host. Python 3.12+ supplies safe tar extraction;
GNU Make 4.3+ supplies grouped JAR targets. The extracted toolchain needs a
compatible glibc host. For a preinstalled toolchain:

```sh
DEVKITPRO=/opt/devkitpro bash scripts/build-all.sh
```

Incremental commands after bootstrapping:

```sh
make -j2 all
make host-test
python3 scripts/verify-artifacts.py
scripts/package.sh
scripts/verify-artifacts.sh
```

The cross compiler uses Cortex-A57/AArch64 code generation, libnx's static PIE
linker specification, `nacptool` and `elf2nro`. NROs are not renamed ELFs.
The verifier checks all segment bounds/alignment, NRO0/ASET, JPEG icon, NACP
identity/version, ELF64 machine 183 and matching GNU build IDs. Host tests also
reject renamed ELFs and truncated files. Debug ELFs and link maps stay in
`build/` for `aarch64-none-elf-addr2line` crash analysis.

## Docker option

```sh
docker build -t switchcraft-build .
docker run --rm -v "$PWD:/src" switchcraft-build
```

The Dockerfile uses the same pinned image. This Docker execution path and the
GitHub Actions workflow are provided but were not exercised end to end here:
Docker's vfs storage duplicated image layers, exhausted the small cloud disk
and failed container creation. The complete build instead used the very same
toolchain extracted by `scripts/bootstrap-toolchain.py`; that path was tested.

In a managed proxy environment keep its configured proxy settings. If TLS
requires the session CA, mount the combined CA bundle read-only and set
`SSL_CERT_FILE` for Python downloads. Do not disable certificate verification.
The Dockerfile does no networked RUN steps. A typical runtime invocation is:

```sh
docker run --rm -v "$PWD:/src" \
  -v /etc/ssl/certs/ca-certificates.crt:/run/combined-ca.pem:ro \
  -e SSL_CERT_FILE=/run/combined-ca.pem switchcraft-build
```

## Java build and patch boundaries

`bootstrap-deps.py` extracts hash-verified miniJVM sources, applies the reviewed
patch and retains original Java sources. `build-minijvm.py` builds a static
AArch64 archive and a host test executable from the interpreter. JIT is disabled,
classic malloc GC is selected, and Immix virtual-memory reservation fails with
ENOSYS rather than pretending mmap works. Process creation and dynamic native
loading fail explicitly. libnx's clocks, pthread compatibility, filesystem and
CSPRNG provide the services actually used. Socket/TLS code links but is untested.

JAR entries have fixed ZIP timestamps. The Java diagnostic tests a real second
JAR, class loading, exceptions, reflection, threading, allocation, file I/O and
a statically registered miniJVM native method. It does not test the standard
JNI Invocation ABI or HotSpot.

## Failed approaches preserved

* Docker container creation: `no space left on device`; switched to OCI extraction.
* OpenGL link: missing C++ and math symbols; fixed link libraries.
* NVK headers: missing `vk_video/vulkan_video_codec_h264std.h`; added matching headers.
* OpenJDK `do_make.sh`: no generated configuration; runner repository absent.
* OpenJDK configure with a downloaded JDK 8: stopped on missing Freetype paths;
  Linux-specific configuration still needs a complete Horizon port.
* miniJVM initial cross-build: missing mmap/dlfcn, Windows-only branches, TLS
  platform gates and C11 `timespec_get`; fixed in the patch and adapter.
* Minecraft AOT upstream script: hardcoded `~/mc-switch`, `~/pz-switch` and
  GraalVM tree unavailable. No AOT binary was fabricated.

The initial minimal NRO's SHA-256 was
`5fbe6c612df56d3e3ff01648b6cd0b6cadbf1eca5d14f7a7de0cbd1dbc5a524c`.
Its source/build log is preserved by commit `7871134`; release hashes differ
because the diagnostic navigation was expanded afterward.
