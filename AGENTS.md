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

The official client was downloaded only to /tmp for research, never committed
or packaged. A Linux Java 25 / llvmpipe Vulkan Demo reference reached the title
screen, including a hash-pinned single-renderer transformation. Evidence is
explicitly HOST ONLY. The pinned genuine Java 25 VM is cross-linked into the
standalone and combined diagnostic NROs; startup is NOT TESTED. Native title
is NOT ACHIEVED. Never turn a cross-link or host screenshot into a device pass.

java-switch exports ABI 1 and a real cross-built OpenJDK 25/Zero runtime, image,
instrumentation and resolver. The regular minecraft-launcher remains VM-free;
its gate must return JS_UNAVAILABLE. The separate switchcraft-java25 NRO links
the VM and composed provider; availability indicates symbols, not startup.
The independent
java-switch task owns the VM, OS/class-library and FFM port. Do not modify that
repository; coordinate via docs/JAVA_INTEGRATION_HANDOFF.md and committed SHAs.
Switchcraft owns Vulkan/SDL/native-library integration and hardware feedback.

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
