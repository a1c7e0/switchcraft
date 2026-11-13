# Switchcraft continuation guide

Write documentation in English; make focused commits and push authorized
changes. Target fixed by the user: 26.4-snapshot-6, Java 25, Vulkan only.
`legacy/1.12.2` preserves the legacy baseline at feb2f4d. Do not rewrite it.
Develop on `main`, which is the GitHub default branch. The owner removed the
temporary mirror and renamed the default branch to `main`. Keep the legacy
branch intact and use explicit expected-head leases when rewriting refs.

## Current status checkpoint (2026-11-13)

R4 is published at `test-suite-2026-11-12-r4` (Switchcraft `e2b9a77`, runtime
`aed255884b8f946a903a4c3d62b2745727f4ef2e`). Its SD ZIP SHA-256 is
`f765f02277c3fa05fdc05b3d5f6dfde544d7fb6e5b45b719732d2f8fbb81aad0`.
Keep published R4 immutable. The owner authorized further fixes and test-package
publication after source, SDK/image, build and artifact verification. R5 uses
`test-suite-2026-11-13-r5`; its new binaries still need physical validation.

New R4 physical feedback contains 21 logs, preserved in
`docs/evidence/device-2026-11-13/` with an English report at
`docs/DEVICE_FEEDBACK_2026_11_13.md`. Firmware is 21.2.0, Application mode.
zero-services-test reached native main and L passed its selected eager C-heap
memory/protection/split-release/ownership/cleanup contract. Other zero-service
buttons were not recorded. Do not treat that as Java or public physical-map
success, or as proof of the earlier R3 launch-failure cause.

The R4 combined NRO logs the correct e2b9a77 source, its complete menu and all
six selected A/X/Y/B/R/L actions. The missing on-screen labels were not caused
by an old combined NRO. R5 explicitly clears/redraws and flushes the menu once,
with the source revision and all controls before input. This still needs a
physical readability check. Existing one-VM-per-process and result panes stay.

R4 again establishes genuine VM creation and java.base loader/error paths,
but native ZIP preflight is followed by missing application classes. Hello,
Java25Smoke and AgentSmokeAgent do not execute; combined X/Y/B/R/L cannot load
NativeSymbols at the ready hook. Graphics, FFM application tests, audio,
shaders and Minecraft are NOT REACHED. Root cause investigation found file
URLs keep an artificial slash before sdmc: in loader/resource native paths;
R5 adapts that conversion with real patched-JDK class/resource regressions.
Do not describe the new fix as hardware-passed before new logs.

Standalone R4 logs contain an old 2d53737-dirty source stamp. Archive/image/link
hashes are coherent with the published SDK; direct diagnostic builds omitted
build-info header refresh. The runtime build script fix refreshes that header
before both direct platform.c compilations. Preserve the raw old stamp and
explain it instead of inferring a stale VM archive.

The ten-module instrumented Minecraft image and native provider families are
real cross-builds. Host evidence includes 91 Switchcraft tests, 22 runtime
tests, JNI/FFM/callbacks, FreeType/OpenAL loopback, STB/Shaderc/SPIRV-Cross,
60 Java Vulkan/VMA frames with validation, and a visually confirmed official
snapshot-6 Demo title under Mesa llvmpipe. Game audio was disabled on that host.
All are HOST ONLY. Module inventory is pinned under
`java_switch.runtime_image_modules`; verify every dynamic image-file hash.
Publish source/debug separately; keep the SD ZIP minimal and preserve saves,
configuration and all unique native/stdout/stderr captures.

Java runtime ownership is a1c7e0/java-switch. Pin its full commit in
`dependencies.lock.json`; do not duplicate its implementation back here.
`python3 scripts/bootstrap-deps.py` clones the pin and shares ignored caches.
`bash scripts/build-all.sh` builds nine NROs, runtime and host tests, renderer
bridge, verifies formats and packages the SD layout. `make host-test` runs the
main suite; external runtime results are in build/java-runtime.log.

src/platform.c owns libnx, metadata.cpp is portable, vulkan.c is the offscreen
baseline, vulkan_present.c owns SDL3/VI/base-profile tests. SDL3 source and the
host CMake wheel are hash-pinned; patches/sdl3-vulkan-only.patch removes EGL
requirements. Keep OpenGL out of main's targets and final linked APIs.

The launcher foundation uses a libnx software framebuffer and pl:u shared fonts
for its controller/touch UI; game rendering remains SDL3/Vulkan. Its console
inspector is retained as a fallback. Instance management uses Prism instance.cfg
and mmc-pack.json with separate game directories. The portable Prism metadata
subset and original pinned sources/provenance are in src/prism_metadata.cpp and
vendor/prism/; the combined launcher carries GPL-3.0-only/Apache-2.0 obligations.
Online catalog/install/verify tasks now use shared Prism metadata, verified
downloads and a cancellable worker. These paths are host-tested and cross-built,
but on-console networking/UI execution is NOT TESTED. Do not describe this as
the complete Qt backend or imply authentication/modloader support.
See docs/PRISM_PORT.md. Host UI previews are never device evidence.

The official client was downloaded only to /tmp for research, never committed
or packaged. Historical Linux Java 25 host evidence reached the
26.4-snapshot-6 title with the strict Vulkan renderer; screenshot and logs are
HOST ONLY. The pinned genuine Java 25 VM is cross-linked into standalone and
combined diagnostic NROs. B7/R2 device results remain scoped to their exact
packages. R3 feedback later established VM creation and `java.base`
class-loading/error paths, but the requested Hello/Smoke classes and agent
class were missing and no Java application workload passed. See
`docs/IMPLEMENTATION_STATUS.md`, `docs/DEVICE_FEEDBACK_2026_11_12.md`, and the
preserved B7 evidence under `docs/evidence/device-2026-11-08/`. Never turn a
cross-link or host screenshot into a device pass.

java-switch exports ABI 1 and a real cross-built OpenJDK 25/Zero runtime, image,
instrumentation and resolver. The regular minecraft-launcher remains VM-free;
its gate must return JS_UNAVAILABLE. The separate switchcraft-java25 NRO links
the VM and composed provider. Symbol availability alone does not establish
startup; the R3 observation of VM creation does not establish successful
application-class execution.
The main assistant may directly edit, commit and push java-switch when needed.
Owner workflow update (2026-11-09): implement runtime fixes, validate them,
commit and push directly. Do not create new java-switch issues unless the owner
explicitly requests one. Issue creation or updates are not a prerequisite for
fixes. Preserve reproduction steps, logs, immutable revisions and validation
limits in commits and repository documentation. Existing issues remain history.
Use an isolated worktree, clean focused commits and immutable full-SHA pins;
keep Switchcraft's pin unchanged unless the integration requires an intentional
pin update. Actively delegate bounded tasks to `gpt-6-luna` with
`reasoning_effort` set to `high`, using disjoint files and explicit ownership.
The main assistant reviews all changes and runs the relevant checks;
agents must not overwrite one another's
work. Coordinate runtime defects and integration through
docs/JAVA_INTEGRATION_HANDOFF.md. Switchcraft owns Vulkan/SDL/native-library
integration and hardware feedback.

`build/libswitchcraft-native.a` is a limited AArch64 static SDL/Vulkan symbol
lookup, not a Java loader. Run scripts/verify-native-link.py after linking. The
feedback collector takes an SD root and creates a new ZIP outside it, with only
allowlisted logs. NRO/SDL/Vulkan hardware results remain NOT TESTED.

The bridge uses the public Java 25 Class-File API and java.instrument; it only
changes the hash-pinned PreferredGraphicsApi.getBackendsToTry method. Native
startup instrumentation on Horizon is cross-built, not device tested. The LWJGL
override reports Horizon truthfully; native FFM SharedLibrary is fail-closed.
Do not bundle game JARs, assets, desktop runtime binaries,
credentials or console keys. Respect original SD saves/configuration.

Use application-mode hbmenu; no Linux/Android boot, patches, proprietary SDK or
overclocking. Docker vfs previously exhausted the small disk; the tested pinned
OCI toolchain extraction fallback is available. CI cross-private checkout needs
JAVA_SWITCH_READ_TOKEN configured in GitHub; do not request or print tokens in
agent conversations. Hardware tests and log export: docs/TEST_PLAN.md.

The 2026-11-08 R2 runtime pin is bff51f38e218af147ca0c9f255fcf1b43be72daf.
Runtime issues4/5/6 retain execution failures; do not close them on cross-build or
host tests. Private HotSpot data memory may eagerly use protected C-heap backing
when checked SystemResourceSizeTotal is zero; public SDK reservations remain
unmapped and raw0xfa01 is Unsupported. Result panes hold until + and never run
another VM. Fatal exceptions keep the stock termination path and capture bounded
relative-PC/register evidence; the exact B7 Java25 crash cause is unresolved.
Unique tick-named Java output and presentation JSON history are allowlisted for
feedback export. The R2 SD ZIP and its Actions assembly path are historical;
the current R4 SD recipe is `scripts/package-device-slim.py`. R4 publication and physical feedback are recorded in the current checkpoint.


The following 2026-11-09 notes are historical. They record R2 physical evidence in
`docs/DEVICE_FEEDBACK_2026_11_09.md`. Java8 diagnostic, private memory L and
300-frame Vulkan presentation passed for R2. Java25 A/X/Y abort at
`memoryReserver.cpp:521`: `protect_memory(..., MEM_PROT_NONE, false)` was rejected.
The later relative-PC `0x3f8be0` is `DefNewGeneration::print_on` during fatal heap
reporting, not evidence of Java execution. At that time R3 was planned to consume
a new immutable runtime pin and the test plan called for the extended L guard
probe before Java A. R3 has since been exercised; use the current R4 test gates
in `docs/IMPLEMENTATION_STATUS.md` and `docs/DEVICE_TEST_QUICKSTART.md`.
The historical R3 user-facing SD ZIP was built by
`scripts/package-device-slim.py` and contained only switch/, necessary
instructions, notices and hashes. For later test packages, publish a matching
source companion and debug symbols separately only after review; do not copy
them onto the SD card.
The collector includes bounded hs_err_pid*.log from the two Java25 app folders.

The historical R3 runtime pin was `4d362d4830cfa4e88313dadfcd3a865e826609a5`.
That pin and its build note describe the archived R3 artifact only; use the
current `dependencies.lock.json` pin when the updated runtime is committed.
Do not reuse R2 generated SDK caches.


Historical published R3 device package: test-suite-2026-11-09-r3. Its executable/source
checkpoint is f715f05ac90080a795f78382ba68e5bb03318e0d; later docs-only commits
need not change that artifact identity. ZIP SHA256:
1b10414234a754cb12291cdbd1d1aa62207fd87136a147e416873e70a904d13f.
Public downloads and server digests are verified in docs/evidence/device-r3-package/.
At that archived revision, the clean Switchcraft suite reported 70 passed and
one optional owned-client test skipped; runtime tests reported 21 passed. Later
R3 device feedback showed `JNI_CreateJavaVM` returned and `vm-ready` was reached,
then Java 25 class lookup failed for Hello/Smoke and the agent. Those logs
establish limited VM startup/class-loader execution, not successful Java
application execution. See the current status checkpoint above.
