# Java SDK integration handoff — Switchcraft to java-switch

This document is a versioned handoff, not a request to modify Java sources in
this repository. Coordination is by committed files and exact SHAs. The Java
agent may not have started or seen this document.

## Pin and evidence

* Pin: `9f6ac4efc04a1750fe54c62d72c4401fda89e68a` in dependencies.lock.json.
  The remote `main` was inspected and matched the pin at this milestone. Do not
  advance it without a separate review, a clean pinned checkout and rebuild.
* SDK header: `include/javaswitch/runtime.h`, `JS_ABI_VERSION = 1`.
  `js_runtime_query`, `js_runtime_launch`, `js_runtime_launch_with_options`,
  `JsRuntimeInfo`, `JsLaunchRequest`, `JsLaunchResult` and status codes are the
  current contract. Header and SDK come from the independent pinned repository.
* Command: `bash scripts/build-all.sh`. It builds the SDK and both Java NROs in
  the pinned dependency checkout, runs its host suite and the Switchcraft suite,
  validates NRO/ELF identities and packages a manifest. Host Java 25 JNI/FFM
  test success is **HOST ONLY**. All native NRO execution is **NOT TESTED**.
* OpenJDK 25 is not built or linked. The `openjdk25` query is unavailable and
  a launch returns `JS_UNAVAILABLE`, stage `runtime-not-linked`. miniJVM is
  Java 8 and must never be accepted as a Java 25 runtime.

## Invocation and lifecycle contract

The request carries ABI and required major version, backend, classpath, class
name in slash-separated JVM form, argument array/count, heap MiB and a VM-ready
hook. Horizon's `sdmc:` paths require `;` as the classpath separator. Additional
JVM options are structured strings passed to `js_runtime_launch_with_options`;
the bridge requires `-javaagent:...` and `java.instrument`. The current adapter
links weak `JNI_CreateJavaVM`, checks actual `java.specification.version`, calls
the VM-ready hook before main, reports stages and destroys the VM. It treats a
second VM per process as unsupported. Static archives may need explicit link
retention for the VM entry point; weak references alone do not extract objects.

A future handoff must specify object ownership, error/exception handling, thread
attachment, callback lifetimes, safepoint/shutdown behavior, and what memory is
committed versus reserved. It must preserve an unavailable result when no real
VM is linked. The `vmem.h` whole-region experiment is owned by java-switch and
is not a completed HotSpot OS layer; its hardware behavior is NOT TESTED.

## Native library boundary

Snapshot-6 metadata lists LWJGL 3.4.3 modules `lwjgl`, `lwjgl-sdl`,
`lwjgl-vulkan`, `lwjgl-vma`, `lwjgl-shaderc`, `lwjgl-spvc`, `lwjgl-freetype`,
`lwjgl-openal`, `lwjgl-stb`, `lwjgl-jemalloc`, and `lwjgl-opengl`. The last is
in official metadata; the verified strict renderer bridge selects Vulkan only.
A listed Java binding JAR is not its native C/C++ implementation. GLFW is not
listed by this snapshot. The actual native dependency graph and initialization
order must still be proven; audio and all game-required components remain open.

Switchcraft's experimental `switchcraft/native_lookup.h` exposes an explicit
static allowlist (`SDL3` and `vulkan` modules) including SDL window/events,
SDL Vulkan surface, and `vkGetInstanceProcAddr`. It is linked into the native
presentation probe. Unknown module/symbol pairs return NULL; use exact C function
prototypes and AAPCS64. It is neither general `dlopen` nor a JVM/FFM loader;
only the listed functions exist, and all hardware calls remain NOT TESTED.
Vulkan instance/device methods must be resolved using `vkGetInstanceProcAddr`
and `vkGetDeviceProcAddr` with their proper dispatch handles, not by flattening
arbitrary names into the static table.

## Request to the independent Java task

1. Provide a committed java-switch SHA, SDK archive/layout, ABI and build command,
   with a reproducible classfile-69 Java 25 JAR test, real JNI invocation and FFM
   downcall/upcall results for both host and Horizon separately. Say explicitly
   when no hardware result exists.
2. Specify and implement an ABI-versioned, typed static native-library/symbol
   resolver callback that can receive a Switchcraft-owned module/name resolver
   without using host `dlopen`; define lifetimes, exact missing-symbol behavior,
   FFM function-address conventions, thread attachment and W^X upcall teardown.
   Propose the interface in that repository; do not assume the present v1 hook
   already supports JVM native library lookup or FFM symbol lookup.
3. Supply a real Java 25 runtime image, class libraries, `java.instrument`,
   class loader and platform services. Document heap/native/GPU memory accounting,
   reservation/partial commit/uncommit/protect behavior and failure Results.
4. Provide `JNI_CreateJavaVM` static-link requirements, allowed options, exact
   VM-ready registration and Java shutdown rules. Supply a minimal Java test that
   calls the same native Vulkan/SDL path, only after the Horizon VM exists.

Switchcraft will review an immutable commit, run the complete build, check ABI,
artifacts and refusal gates, and only then update its lock. The next runtime
integration order is classfile-69 Java -> real Java Vulkan window -> pinned
Minecraft Demo; no title, Fabric or gameplay claim follows from the native probe.
