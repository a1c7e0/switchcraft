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
`bash scripts/build-all.sh` builds six NROs, runtime and host tests, renderer
bridge, verifies formats and packages the SD layout. `make host-test` runs the
main suite; external runtime results are in build/java-runtime.log.

src/platform.c owns libnx, metadata.cpp is portable, vulkan.c is the offscreen
baseline, vulkan_present.c owns SDL3/VI/base-profile tests. SDL3 source and the
host CMake wheel are hash-pinned; patches/sdl3-vulkan-only.patch removes EGL
requirements. Keep OpenGL out of main's targets and final linked APIs.

The official client was downloaded only to /tmp for research, never committed
or packaged. A Linux Java 25 / llvmpipe Vulkan Demo reference reached the title
screen, including a hash-pinned single-renderer transformation. Evidence is
explicitly HOST ONLY. Horizon Java 25 is NOT IMPLEMENTED; native title is NOT
ACHIEVED, all physical execution NOT TESTED. Never turn these into a pass based
on a cross-link or host screenshot.

java-switch exports a versioned C SDK, actual standard JNI adapter and libffi
AAPCS64/W^X prerequisites. JNI/FFM tests pass on host. No Horizon libjvm is linked,
so the launch gate must return JS_UNAVAILABLE; do not add a fake Play action.
OpenJDK 25/Zero configuration fails at unsupported OS elf. Port actual memory,
exceptions, threads/TLS, class libraries, static symbols and fallback FFM next.

The bridge uses the public Java 25 Class-File API and java.instrument; it only
changes the hash-pinned PreferredGraphicsApi.getBackendsToTry method. No account
or authentication bypasses. Native loader/Java 25 instrumentation on Horizon
is still absent. Do not bundle game JARs, assets, desktop runtime binaries,
credentials or console keys. Respect original SD saves/configuration.

Use application-mode hbmenu; no Linux/Android boot, patches, proprietary SDK or
overclocking. Docker vfs previously exhausted the small disk; the tested pinned
OCI toolchain extraction fallback is available. CI cross-private checkout needs
JAVA_SWITCH_READ_TOKEN configured in GitHub; do not request or print tokens in
agent conversations. Hardware tests and log export: docs/TEST_PLAN.md.
