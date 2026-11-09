# Switchcraft continuation guide

Write documentation in English; make focused commits and push authorized
changes. Target fixed by the user: 26.4-snapshot-6, Java 25, Vulkan only.
`legacy/1.12.2` preserves the legacy baseline at feb2f4d. Do not rewrite it.
Develop on `main`, which is the GitHub default branch. The owner removed the
temporary mirror and renamed the default branch to `main`. Keep the legacy
branch intact and use explicit expected-head leases when rewriting refs.

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
or packaged. Linux host Java 25 has reached the 26.4-snapshot-6 title with the
strict Vulkan renderer; screenshot and logs are HOST ONLY. The pinned genuine
Java 25 VM is cross-linked into the standalone and combined diagnostic NROs.
Original B7 device feedback now establishes native/FFI/SafeFetch and 300-frame
SDL3/VI rendering results; Java8 file I/O and physical mappings failed and every
Java25 attempt aborted before observed Java output. New R2 fixes remain device
unverified. Preserve this distinction; see docs/evidence/device-2026-11-08/.
Never turn a cross-link or host screenshot into a device pass.

java-switch exports ABI 1 and a real cross-built OpenJDK 25/Zero runtime, image,
instrumentation and resolver. The regular minecraft-launcher remains VM-free;
its gate must return JS_UNAVAILABLE. The separate switchcraft-java25 NRO links
the VM and composed provider; availability indicates symbols, not startup.
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
feedback export. The full R2 SD ZIP is built by scripts/package.py; public release
parts are internal transport and the Actions publisher emits a single user ZIP.


2026-11-09 R2 physical evidence is preserved in
`docs/DEVICE_FEEDBACK_2026_11_09.md`. Java8 diagnostic, private memory L and
300-frame Vulkan presentation passed for R2. Java25 A/X/Y abort at
`memoryReserver.cpp:521`: `protect_memory(..., MEM_PROT_NONE, false)` was rejected.
The later relative-PC `0x3f8be0` is `DefNewGeneration::print_on` during fatal heap
reporting, not evidence of Java execution. R3 consumes a new immutable runtime
pin to fix both paths; new binaries remain device-unverified. Run the extended
L guard probe, then one fresh Java25 A; continue X/Y/combined only after Hello.
The user-facing SD ZIP is built by `scripts/package-device-slim.py` and contains
only switch/, necessary instructions, notices and hashes. Publish corresponding
source and matching debug symbols separately; do not copy them onto the SD card.
The collector includes bounded hs_err_pid*.log from the two Java25 app folders.

The R3 runtime pin is `4d362d4830cfa4e88313dadfcd3a865e826609a5`. Build it with instrument support, package and verify its actual SDK/image first, then use
`JAVA_SWITCH_SOURCE` for downstream builds. Do not reuse R2 generated SDK caches.


Published R3 device package: test-suite-2026-11-09-r3. Its executable/source
checkpoint is f715f05ac90080a795f78382ba68e5bb03318e0d; later docs-only commits
need not change that artifact identity. ZIP SHA256:
1b10414234a754cb12291cdbd1d1aa62207fd87136a147e416873e70a904d13f.
Public downloads and server digests are verified in docs/evidence/device-r3-package/.
Final clean Switchcraft suite: 70 passed, one optional owned-client test skipped;
runtime: 21 passed. Physical R3 Java25 startup/execution remains NOT TESTED.
