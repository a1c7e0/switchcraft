# Mainline update: fixed snapshot 6

Java runtime ownership moved to [a1c7e0/java-switch](https://github.com/a1c7e0/java-switch).
Its exact commit is in dependencies.lock.json. The preserved original investigation
below describes the legacy baseline; mainline integration decisions are updated here.

| Source / pin | Inspected implementation and result | Integration / limits / license |
| --- | --- | --- |
| etonedemid/SDL `1e3b67ef787c0fdba47b42fc663c70613c8b04db` | Read Switch video/Vulkan/input code and CMake. Real SDL3 VI surface/window path, but unconditional EGL references broke Vulkan-only builds. Patched guards/window creation; static library and NRO link succeed with GL/EGL off. | Selected native SDL3/input/VI adapter. Zlib license retained. Hardware NOT TESTED. |
| OpenJDK jdk25u `275848b087112429235f4f235822e294a1a288ef` | Read Zero foreignGlobals, fallback linker Java/C and autoconf. Actual configure reaches unsupported OS elf. Zero's assembly foreign linker is absent, but libffi fallback is enabled by default. | Required runtime source-port route; no Horizon VM binary. GPL/ClassPath/assembly exceptions retained per source; no desktop runtime redistributed. |
| libffi `v3.8.0`, hash in Java repository | AAPCS64 source/configuration compiles. Replaced malloc-backed executable closure allocation with real libnx JIT RW/RX/cache/teardown APIs; native downcall/upcall NRO builds. | Java repo SDK prerequisite, hardware NOT TESTED. MIT notice/source retained. |
| Temurin `25.0.5+8`, locked SHA-256 | Actual host JNI creation/native registration/options/FFM downcall/upcall/teardown pass. Snapshot 6 Demo title passes with strict Vulkan transformation. | Host build/reference tool only, no Horizon runtime claim or bundled Linux JDK. |
| Official snapshot 6 metadata/client | Metadata SHA-1 `04be0f389fdac9f1c8b9b551c1e717104a08899d`, client SHA-1 `8a97d5dafe80783525a2807b220527b65df724a5`. Inspected VulkanFeatureSets, VulkanInstance, SDL Window and renderer preference bytecode. | Fixed Java25/Vulkan1.2 base/SDL3 target. Client retains GL fallback; original hash-pinned renderer transformation removes that fallback. No game bytes/credentials redistributed. |

Renderer-class SHA-256 is pinned in profiles/26.4-snapshot-6.json. A public
Class-File-API/Java-instrumentation bridge transforms one method; synthetic
fixtures and the actual host title test pass. A custom child-loader attempt
failed, so the final implementation preserves the normal loader. No account
or authentication code is patched. Full source OS/FFM/native module integration
on Horizon remains open. Read HOST_REFERENCE.md and the independent Java port
notes before interpreting the host title screenshot.

## Preserved original upstream investigation

# Upstream source research

Sources were inspected on 2026-11-02. Revisions are immutable observations, not
claims that the default branch will remain unchanged. The date records the
session clock. Hardware claims in upstream READMEs are upstream reports only.

## Required candidates

| Source URL and revision | Source/build evidence | Maintenance and confirmed limits | Decision and license/distribution |
| --- | --- | --- | --- |
| [danfromtico/mesa-switch](https://github.com/danfromtico/mesa-switch), `0ff52079ca9e9e837ed27eb95a8d239f439a1864` (2026-10-12) | Inspected `build-opengl.sh`, `build-switch.sh`, crossfiles, `src/nouveau/horizon/nouveau_horizon_device.c` and `src/nouveau/vulkan/nvk_physical_device.c`. Real GM20B/nvhost adaptation; OpenGL and NVK build paths differ. | Recent source changes. Full modern build needs Rust, bindgen, LLVM/CLC/SPIR-V host tools and custom cross configuration; not rebuilt in this run. The source explicitly marks UMA, uses GM20B classes and gates features by GPU generation. | Keep as upgrade candidate. Delivered OpenGL uses the existing pinned devkitPro Mesa package; delivered NVK uses the separate public archive below. Mesa is mostly MIT with per-file BSD/SGI/other notices; carry notices and audit selected source paths. No conformance assumption. |
| [jhuz0/nvk-switch](https://github.com/jhuz0/nvk-switch), `080a647b0eb448631874da25d26826d491ddcf33` (2026-07-24), release `nvk-switch-mesa-25.0.7-r1` | Inspected full `.github/workflows/build-nvk.yml`: archive aggregation, Expat inclusion, strong-symbol localization, loaderless entrypoints, `nvk_compat.c`, nv50_ir inclusion and Maxwell environment constructor. Downloaded and hash-verified release library; actually linked `vulkan-test.nro`. | Repository is small packaging infrastructure. Release workflow run `30142928043` succeeded at that commit. Binary uses nxvk `switch-mesa-25.0.7`; exact nxvk commit is not recorded in release provenance. GM20B is deliberately exposed with `NVK_I_WANT_A_BROKEN_VULKAN_DRIVER=1`. | Selected for independently testable Vulkan. Archive SHA-256 `4ab244f982dc078aaff8c58640d7cf8a0f3ab43bbf2daadfd00c02fbf352af86`; library `ff65a74b46fe749f6be73eac3c8968d70e312c7646f815f26b69f4aa35737d26`. Mesa/nxvk/Expat permissive licenses; included upstream NOTICE. Static driver source rebuild remains a provenance task. |
| [devkitPro/deko3d](https://github.com/devkitPro/deko3d), `373bfd43d8b2d805fa2eb7d406dbb823032df958` (2026-10-17) | Inspected C++ renderer/device sources, public include API, Makefile and license; checked devkitPro example shaders. Provides native GM20B command/rendering API, not OpenGL or Vulkan. | Recent fix at inspected head. Useful native renderer; cannot directly satisfy LWJGL's OpenGL/Vulkan API. Not independently built here. | Console fallback already comes from libnx. Keep deko3d as future launcher renderer; no new Vulkan-to-deko3d layer. Zlib license with origin/alteration notice requirements. |
| [autorunhq/autorun](https://github.com/autorunhq/autorun), `1ac9b6cf37b90f2d5783dd7ef389bebbe1c68877` (2026-10-16) | Inspected Wine `configure.ac`, server/process/thread source layout and runtime integration documents, not just screenshots. Combines Windows compatibility, translators and Mesa in a single Horizon process. | Active source; broad, overlapping infrastructure. Installation documentation includes custom Mesosphere/loader changes for low addresses, outside this task's no-patch baseline. It is not a Java runtime. | Research reference only. No code or system modification reused. Wine code LGPL-2.1 and component-specific licenses; static integrations would need their own distribution review. |
| [autorunhq/switch-dev](https://github.com/autorunhq/switch-dev) | Git clone returned `Repository not found`. | No revision, source, buildability, maintenance or license could be confirmed. This may reflect availability/access; no inference of a working runtime. | No dependency. |
| [MiaouMeowMiaou/openjdk-switch](https://github.com/MiaouMeowMiaou/openjdk-switch), `9fb602f2db93ba8870fcaa30dc5fb2a60b783d36` (2026-08-12), branch `aarch64-shenandoah-jdk8u272-b10` | Inspected `do_make.sh`, build scripts, `hotspot/src/os/linux/vm/os_linux.cpp` and AArch64 OS source. Actual RW/RX alias translations and exception adaptations exist. Ran upstream build/configure attempts. | Partial research port; scripts contain developer-local MSYS paths and copy to a sibling `switch-java-runner`. That runner URL returned 404. HotSpot declares external `switch_jit_alloc`, `g_code_addr`, `g_code_dummy`, `g_jit_initialized` from absent compatibility/runner code. Linux mmap/dlsym/signals are still referenced. Configuration with JDK 8 stops at Freetype setup; this is not proof that installing Freetype completes the Horizon port. | Preserve as primary future OpenJDK path, not a delivered runtime. GPL-2.0 plus OpenJDK assembly/ClassPath exceptions where applicable; complete corresponding source, runtime/class library and patches would be needed for binary distribution. No `libjvm.a` was produced. |
| [PojavLauncherTeam/PojavLauncher](https://github.com/PojavLauncherTeam/PojavLauncher), `b12ad048157b3aa255d078c235dd4571e1900309` (2025-09-23) | Inspected JNI `jre_launcher.c`, `utils.c`, `environ/environ.h`, Android.mk and native hooks. Uses `dlopen(libjli.so)`, Android native windows and custom LWJGL/GLFW hooks. | Latest inspected commit explicitly discontinues project. Android APK/NDK build does not target Horizon. Android JREs and native libraries cannot be linked as libnx binaries. | Architecture reference only; no Android runtime or launcher copied. LGPL-3.0 and multiple dependency licenses; a port would require ABI/service replacements and license notices. |
| [etonedemid/minecraft-switch](https://github.com/etonedemid/minecraft-switch), `ed1e108986330d8d4943a92ed4ee88a457795b99` (2026-10-21) | Inspected and attempted `build-nro.sh`; inspected `build-a64.sh`, `build-natives.sh`, `fetch.py`, JNI generation tooling and reachability metadata. Real GraalVM relocatable-image approach for fixed Minecraft 1.12.2 + OptiFine. | Recent but not self-contained. Requires `~/pz-switch/horizon`, musl-nx, `prelink-j.sh`, GraalVM 25, JDK AWT static archives, custom LWJGL jars and user-prepared merged game JAR. `build-a64.sh` requests `-J-Xmx24g`. Actual build attempt stops at hardcoded `~/mc-switch` path. The referenced `etonedemid/pz-switch` URL returned 404. | Separate AOT research backend only. No AOT artifact produced. No top-level project license found in inspected tree; do not copy its implementation without resolving terms. Minecraft/OptiFine cannot be redistributed by this package. AOT fixed-image behavior is not arbitrary JAR/Mod loading. |

## Dependencies actually integrated

| Source | Pin / verification | Integration and limitations | License handling |
| --- | --- | --- | --- |
| [digitalgust/miniJVM](https://github.com/digitalgust/miniJVM) | `87c9808145fabbf13c7a0d6b6d1e5bfbdbdba5a8`; archive SHA-256 in lock | Inspected interpreter, class loader, JVM lifecycle, OS adapters, GC, native method registry and Java class library. Built native interpreter, patched Horizon archive and `java-test.nro`; same adapter passes host JAR/thread/reflection/file/native-bridge suite. Limited class library fails real Minecraft bootstrap. JIT/Immix/process/dynamic libraries disabled. | C runtime MIT; Java directory GPL-2.0 with retained per-file exception notices. Entire Java source and modified C source accompany package. Upstream's suggestion that prebuilt JARs avoid GPL obligations is not adopted. |
| [switchbrew/libnx](https://github.com/switchbrew/libnx) | Package `4.12.0-1` inside digest-pinned image; LICENSE from `v4.12.0` | Used actual headers and linked libnx for input, console, FS, threads, memory queries, clocks, lifecycle and next-load. | ISC notice retained in `licenses/`. |
| [switchbrew/switch-examples](https://github.com/switchbrew/switch-examples) | `669786898205b7beb25ff1731e72982e6d0397d3` | Inspected application template and OpenGL simple triangle lifecycle. New application code written independently; no example assets copied except libnx's toolchain default icon. | Preserve libnx/default-icon provenance through toolchain packaging. |
| devkitPro Mesa / GLAD / Nouveau portlibs | Image pin, package `switch-mesa-20.1.0-5`, GLAD `0.1.27-1` | Actual EGL/OpenGL static link successful after adding C++/math libraries. Version/extension capability remains hardware-measured, not assumed from package version. | Mesa/license notices retained. Toolchain runtime/newlib/libstdc++ carry their upstream terms and GCC Runtime Library Exception where applicable. |
| [Khronos Vulkan-Headers](https://github.com/KhronosGroup/Vulkan-Headers) | `v1.4.305`, SHA-256 locked | NVK release omitted `vk_video/`; matching header release fixes compile. | Apache-2.0 / MIT texts retained. |
| [nlohmann/json](https://github.com/nlohmann/json) | `v3.11.3`, vendored header SHA-256 locked | Robust real JSON parser shared by host/Horizon; exceptions caught at UI boundary. | MIT notice retained. |
| Temurin JDK 8 | `jdk8u504-b01`, SHA-256 locked | Host build tool only. Official GitHub release used after Adoptium API returned HTTP 403. Not a console runtime. | Not shipped in SD package. |

## Other ecosystems and integration choices

SDL2 and GLFW portlibs are present in the pinned toolchain, but console UI plus
direct EGL reduce dependencies for this milestone. OpenAL Soft, Prism and
Fabric remain source-research/implementation follow-ups; they are not bundled
or claimed to be integrated. Fabric requires runtime class transformation,
Mixins and compatible native bridges, beyond a successful class-loading test.
GraalVM Native Image remains a separate fixed-image backend with closed-world
constraints, not a substitute for arbitrary Java dependencies or modern JVMs.

Official Mojang version manifests were fetched, inspected and processed locally;
exact copies are retained as metadata evidence. For one isolated host bootstrap,
the official 1.12.2 client and Java libraries were downloaded to `/tmp`, checked
against metadata SHA-1 values, and executed without credentials or fabricated
tokens. The run failed at missing class-library/LWJGL functionality. Those game
JARs are excluded from Git, SD layout and release archives.
