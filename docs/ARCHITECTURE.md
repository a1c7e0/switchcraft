# Mainline architecture — snapshot 6 / Vulkan

Solid paths have implemented and compiled code. Dashed paths are unavailable
runtime integration. **Every Horizon path is hardware NOT TESTED.** Host reference
execution is separate and is not a Switch execution backend.

```mermaid
flowchart TD
  HB[Application-mode hbmenu] --> D[Native platform diagnostics]
  D -->|next-load replacement| V[NVK offscreen tests]
  D -->|next-load replacement| W[SDL3 / VI swapchain + gamepad + exact base profile]
  D --> L[Snapshot 6 inspector / launch gate]
  D --> J[Independent Java 8 test NRO]
  D --> F[Independent AAPCS64 / W^X FFI NRO]
  L --> M[Portable metadata / inheritance / rules / classpath planner]
  M --> INSTALL[Read-only standard .minecraft]
  M --> PLAN[Strict Vulkan plan / separate runtime logs and config]
  L --> SDK[Pinned java-switch C SDK / JNI adapter]
  SDK -. no VM linked .-> JVM[Horizon OpenJDK 25 / class library / JNI / FFM]
  JVM -. required .-> LW[Static LWJGL / SDL3 / VMA / shaderc / SPVC / audio]
  W --> LOOKUP[Limited static SDL / Vulkan symbol lookup]
  LW -. future resolver handoff .-> LOOKUP
  LW -.-> NVK[Native NVK + Horizon GPU services]
  JVM -.-> BRIDGE[Java instrumentation / pinned Vulkan-only method transformation]
  BRIDGE -.-> MC[Minecraft title / world / future Fabric]
  J --> MINI[miniJVM Java 8 interpreter + original test JARs]
  F --> FFI[libffi AAPCS64 / libnx RW-RX code memory]
```

`java-switch` owns JVM adapters, interpreter, original Java workloads, SDK and
libffi code. This repository consumes a fixed commit, builds/repacks its NROs and
links its SDK. `src/platform.c` owns Horizon console/input/SD/memory/threads;
`metadata.cpp` is shared with host tools; `vulkan_present.c` owns SDL/VI behavior.

The launcher cannot start a Java 25 game because the actual VM is absent. Its
real SDK call returns JS_UNAVAILABLE/runtime-not-linked. No Play action claims
otherwise. Next-load replaces the current NRO via hbmenu; there is no fork/exec
or simultaneous launcher/game process. A future Java VM enters the same process
or uses an explicit serialized handoff.

## Graphics path

```mermaid
flowchart LR
  INPUT[Joy-Con / Pro / USB input] --> SDL[Patched SDL3 Switch driver]
  SDL --> WIN[libnx NWindow]
  SDL --> VI[VK_NN_vi_surface]
  VI --> SWAP[VK_KHR_swapchain]
  SWAP --> NVK[Static Mesa NVK / GM20B]
  NVK --> DISPLAY[Horizon presentation]
  PROFILE[Exact base-feature queries] --> NVK
  JAVA[Future LWJGL FFM calls] -.-> SDL
  JAVA -.-> NVK
```

SDL3 is configured with GL/OpenGL ES/EGL disabled. Its native Switch backend
previously referenced EGL even for Vulkan windows; the patch guards/removes
those dependencies. Native linked symbol checks contain SDL/Vulkan entries and
no EGL/OpenGL API functions. This does not prove Java bindings or hardware output.

Presentation uses a graphics/present queue, actual surface capabilities/formats,
FIFO, per-image render-finished semaphores, finite acquire/fence waits and a
conservative queue drain. It clears animated colors over up to 300 frames and
records SDL gamepad events. The independent NVK NRO retains transfer/readback and
a shader-rendered offscreen triangle. Driver hangs remain possible.

## Runtime and startup

```mermaid
flowchart TD
  SCAN[Scan version JSONs] --> RESOLVE[Resolve inheritance / rules / dependencies]
  RESOLVE --> REQUIRE[Java25 + classfile69 + Vulkan profile]
  REQUIRE --> GATE[Check actual runtime availability]
  GATE -->|current result| BLOCK[Log runtime-not-linked; no game invocation]
  GATE -. future VM available .-> CREATE[JNI_CreateJavaVM + actual version check]
  CREATE -.-> MODULES[Static FFM/JNI native lookup and required modules]
  MODULES -.-> PATCH[Verify class hash; select Vulkan backend only]
  PATCH -.-> MAIN[Invoke Minecraft main with isolated instance]
  MAIN -.-> TITLE[Title / world]
  CREATE -. failure .-> ERROR[Log stage; teardown / return or process recovery]
  MAIN -. failure .-> ERROR
```

The SDK's JNI creation/options/native-registration/teardown and FFM tests pass
against a real **host** Java 25 VM. OpenJDK Zero defaults to a libffi fallback
foreign linker, which motivates the native AAPCS64 and W^X tests. A complete
Horizon OS/class-library implementation remains required; mmap/dlopen/signals
cannot be assumed from Linux or replaced by fake successful stubs.

The strict renderer bridge uses Java 25's public Class-File API/instrumentation
and checks the exact original renderer-class hash. It modifies only backend
selection. It preserves the normal loader and all authentication code. Its JAR
contains original source-generated code, not game class bytes.

## Filesystem and failure boundaries

```text
sdmc:/switch/{switch-diagnostics,vulkan-test,vulkan-present,minecraft-launcher,java-test,ffi-test}/<name>.nro
sdmc:/switch/mc-runtime/
  config/{launcher.example.json,launcher.json}
  logs/{<application>.log,launch-plan.json,snapshot-vulkan.json}
  profiles/26.4-snapshot-6.json
  launchers/switchcraft-launcher-bridge.jar
  runtimes/minijvm/minijvm_rt.jar
  tests/{diagnostic-tests,dependency,java25-tests,user}.jar
  instances/{java-smoke,test/<version>}/
  licenses/
sdmc:/minecraft/.minecraft/{versions,libraries,assets,mods,config,saves,resourcepacks,shaderpacks}/
```

The game installation is read only. Paths/classpaths use Horizon-aware separators;
credentials remain unresolved and are not acquired/logged. Diagnostic writes are
isolated. Supported API failures are reported; pending GPU work may require
process exit, and a hung driver/JVM may require HOME/relaunch. Runtime target,
source revision, hashes and NOT TESTED hardware state are in the manifest.

The standalone [architecture.svg](architecture.svg) reflects the same boundaries.
