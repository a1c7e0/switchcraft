# Build and reproducibility

Mainline target: 26.4-snapshot-6 / Java 25 / Vulkan. Legacy builds are on branch
legacy/1.12.2; Java runtime builds are owned by a1c7e0/java-switch.

```sh
bash scripts/build-all.sh
```

Requires Linux x86_64, Python 3.12+, GCC/G++, GNU Make, patch, Git and HTTPS access.
Access to the private Java repository is necessary. `DEVKITPRO` may select an
existing toolchain; `JAVA_SWITCH_SOURCE` may select a clean checkout at the locked
revision. Otherwise dependencies are created under ignored `.deps/`.

The exact pins/hashes are in dependencies.lock.json. Toolchain: devkitA64 GCC
15.2.0-7, binutils 2.45.1-2, newlib 4.6.0.20260123-4, libnx 4.12.0-1, from the
fixed devkitPro image digest. NVK is the hash-pinned Mesa-25.0.7 archive. SDL3
source is etonedemid/SDL 1e3b67ef787c0fdba47b42fc663c70613c8b04db plus the local
Vulkan-only patch. Host CMake 4.4.4's exact wheel is hash-pinned. Java includes
its own miniJVM/libffi/Temurin build-tool locks; no Linux JVM is shipped for Horizon.

The pipeline checks out Java at the exact commit, builds/tests its standalone
NROs and reusable SDK, builds SDL3 with GL/EGL disabled, links the native apps,
builds the original renderer bridge and LWJGL overrides with Java 25, runs host
tests and packages. With a prepared runtime checkout, the same build can be run
as `JAVA_SWITCH_SOURCE=/path/to/clean/pinned/java-switch bash scripts/build-all.sh`.
The checkout must contain its verified instrument-enabled SDK and runtime output;
if absent the build invokes `bash scripts/build-openjdk25-runtime.sh --with-instrument`.
The first such build may be large and slow. Earlier build issues and their
upstream fixes are recorded in JAVA_INTEGRATION_HANDOFF.md.
The baseline SDK has a real JNI adapter without a VM. The instrument-enabled
runtime is separately built and linked into java25-test and switchcraft-java25.
Symbol availability does not establish VM startup. Host JNI/FFM tests load a
host JDK intentionally.

```sh
make -j2 all
make host-test
python3 scripts/verify-artifacts.py
scripts/package.sh
scripts/verify-artifacts.sh
```

NRO verification checks NRO0/ASET, aligned bounded segments, NACP title/author/
version, JPEG icon and matching AArch64 ELF build IDs. Repackaged Java artifacts
retain JavaSwitch identity. Debug ELFs/maps remain under build for crash
symbolication. Artifacts are never renamed ELFs or placeholders.
`dist/switchcraft-debug-symbols.zip` contains matching debug ELFs and available
linker maps; `dist/switchcraft-native-sdk.tar.gz` contains the experimental static
symbol lookup and its contract. Neither constitutes a working Horizon JVM.

To test the actual hash-verified snapshot client without redistributing it, set
`SWITCHCRAFT_CLIENT_JAR` to a locally held client JAR before `make host-test`.
The test rejects a wrong client SHA-1 and renderer-class SHA-256; only temporary
transformed class bytes are written. The default suite skips this optional test.

Build logs: build/cross-build.log, build/host-tests.log, build/java-runtime.log
and build/sdl3-build.log. Final source pins, hashes and hardware status are in
dist/manifest.json and SHA256SUMS. Every NRO is hardware NOT TESTED.

Dockerfile uses the same pinned image; Docker vfs previously exhausted the
7.9-GB cloud disk. The tested fallback extracts/validates OCI index, platform
manifest and layers directly. Docker/CI are not claimed as executed merely
because definitions exist. GitHub Actions needs a read-only JAVA_SWITCH_READ_TOKEN
secret to check out the second private repository. No credential value is
requested by these scripts. Keep session proxy/CA settings and TLS verification.

The bridge uses Java 25's public Class-File API; it does not bundle or rewrite
a game JAR on disk. Runtime transformation is limited by class SHA-256 and method
signature. The built bridge is packaged as an original JAR under mc-runtime/launchers.
The runtime image contains java.instrument, but startup agents have not run on
Horizon. The snapshot-specific bridge remains unverified on that VM.

The earlier `unsupported operating system elf` experiment predates the independent
java-switch Horizon port. The current pinned Zero archive, instrument providers,
two-module image and diagnostic NRO cross-build; hardware execution is untested.
