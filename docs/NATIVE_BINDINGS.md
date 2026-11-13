# Snapshot-6 native binding status

Snapshot metadata lists LWJGL core, SDL, Vulkan, VMA, shaderc, SPIR-V Cross,
FreeType, OpenAL, STB, jemalloc and OpenGL. The strict renderer transformation
selects Vulkan only; the OpenGL metadata entry remains part of the official
client. The SDL3/VI executable is native code, not an LWJGL implementation.

`build/libswitchcraft-native.a` contains an AArch64, exact-name resolver.
`scripts/generate-sdl-symbols.py` preprocesses the public SDL headers with the
Switch target compiler and intersects active `SDL_DECLSPEC`/`SDLCALL`
declarations with global function definitions in the built SDL archive. At the
pinned build, the generated `build/sdl_symbols_generated.h` table includes
1,242 SDL functions across 52 headers; `build/sdl_symbols_generated.json`
records the archive and output hashes. Functions missing from the archive or
inactive for Switch are not emitted. The table resolves genuine linked SDL
addresses; it does not implement each Java binding signature. Vulkan exposes
only global `vkGetInstanceProcAddr`; device functions remain under Vulkan's
normal dispatch. `tests/test_sdl_exports.py` checks fixture intersection and
regenerates the real table with the pinned AArch64 compiler. The
`vulkan-present` NRO links the same table, `scripts/verify-native-link.py`
checks linked functions and absence of GL/EGL entry points, and unknown names
return NULL.

Native WSI uses pinned etonedemid/SDL, zlib license, plus Mesa NVK and libnx;
revisions and archive hashes are in dependencies.lock.json. LWJGL's core
provider contains 1,957 actual JNI exports and two lifecycle entries, including
libc, libffi, thread TLS and Java callbacks. STB/VMA use genuine upstream JNI
sources. FreeType uses the target FreeType archive; OpenAL Soft is built with
the SDL3 backend. Shaderc and SPIRV-Cross compile their pinned upstream C APIs.
See the focused build documents for each family's measured verification.
Jemalloc is not provided: the launch selects LWJGL's real system allocator.
OpenGL remains excluded from the renderer, and no Joy-Con gameplay result is
claimed. See [the optional-native audit](NATIVE_STARTUP_AUDIT.md).

## Horizon platform and library initialization

The modified LWJGL 3.4.3 `Platform` and `Library` sources under
`vendor/lwjgl-horizon/` derive from upstream commit
`30fac9b95f99cda97312232be25ba55297bf9951` under its BSD license. The compiled
override JAR precedes the original classpath entry for the exact snapshot.
Horizon is an explicit enum with AArch64 recognition and no Linux identity.
JNI load requests are passed by name to the JVM's real static loader; missing
`lwjgl` core providers fail normally. The Horizon `SharedLibrary` adapter now
maps the exact LWJGL 3.4.3 SDL3, Vulkan, FreeType, OpenAL, Shaderc and
SPIRV-Cross requests to their real static modules via `NativeSymbols`.
The exact alias table is in [LWJGL_HORIZON_COMPAT.md](LWJGL_HORIZON_COMPAT.md).
STB/VMA use the JVM's static JNI loader instead. Exact lookup returns zero for missing
symbols; unsupported names or unavailable modules throw `UnsatisfiedLinkError`.
It reports no filesystem path or dynamic-library handle, and `free()` does not
unload process-owned code. The override JAR includes the `NativeSymbols` Java
bridge required by this path. A host test using the real pinned LWJGL JAR and a
host-only JNI/FFM fixture calls a native `SDL_GetVersion` symbol and checks
missing-module, missing-symbol, UTF-8 buffer, and ownership behavior. This is
host evidence only; it does not establish Horizon execution or full LWJGL
coverage. `APIUtil.apiCreateLibrary` has no Horizon branch, so the override
routes supported Horizon loads directly through the adapter and avoids that
desktop-only factory.

The combined Java25 diagnostic composes the generated JDK provider with the
application modules before the JVM seals the resolver. JDK entries take
precedence; module-name collisions are rejected. Missing entries return zero.
It links the real agent and VM archives and checks required definitions.
Its explicit diagnostic workloads cover Hello, JNI/FFM, LWJGL core, Java
SDL/Vulkan/VMA presentation, FreeType/OpenAL loopback, and STB/shader utilities.
Only actual completion markers establish a workload result. In particular,
OpenAL loopback PCM does not establish physical audio output, and creating a
Vulkan swapchain does not establish presentation. All new Horizon workloads
require device evidence; historical R3 VM startup and class-loader failures
remain recorded separately in [DEVICE_FEEDBACK_2026_11_12.md](DEVICE_FEEDBACK_2026_11_12.md).
