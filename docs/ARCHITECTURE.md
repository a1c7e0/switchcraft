# Mainline architecture — snapshot 6 / Vulkan

Solid paths have implemented and compiled code. Dashed paths are unavailable
runtime integration. **Every Horizon path is hardware NOT TESTED.** Host reference
execution is separate and is not a Switch execution backend.

```mermaid
flowchart TD
  HB[Application-mode hbmenu] --> D[Native platform diagnostics]
  D -->|next-load replacement| V[NVK offscreen tests]
  D -->|next-load replacement| W[SDL3 / VI swapchain + gamepad + exact base profile]
  D --> L[Switch-style launcher / instance manager / launch gate]
  L --> PRISM[Portable Prism component metadata / isolated instance profiles]
  D --> J[Independent Java 8 test NRO]
  D --> F[Independent AAPCS64 / W^X FFI NRO]
  L --> M[Portable metadata / inheritance / rules / classpath planner]
  M --> INSTALL[Read-only standard .minecraft]
  M --> PLAN[Strict Vulkan plan / separate runtime logs and config]
  L --> SDK[Pinned java-switch C SDK / JNI adapter]
  D --> VMTEST[Java25 and combined resolver diagnostics]
  VMTEST --> JVM[Cross-linked Horizon OpenJDK 25 / class library / JNI / FFM]
  SDK -. baseline launcher VM-free .-> JVM
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

The Minecraft launcher remains VM-free and returns JS_UNAVAILABLE/runtime-not-linked.
Separate Java25 diagnostics link the actual VM in-process; VM startup, the
composed provider and all Java execution remain untested on Horizon. No Play
action claims Minecraft is ready. The diagnostics terminate their application
process after a VM session; there is no fork/exec or VM reuse in the loader.

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
against a real **host** Java 25 VM. The independent Horizon Zero VM, native
providers and java.base/java.instrument image are cross-built; no physical VM
startup is established. Unsupported OS services remain explicit failures.

The strict renderer bridge uses Java 25's public Class-File API/instrumentation
and checks the exact original renderer-class hash. It modifies only backend
selection. It preserves the normal loader and all authentication code. Its JAR
contains original source-generated code, not game class bytes.

## Filesystem and failure boundaries

```text
sdmc:/switch/{switch-diagnostics,vulkan-test,vulkan-present,minecraft-launcher,java-test,ffi-test,zero-services-test,java25-test,switchcraft-java25}/<name>.nro
sdmc:/switch/mc-runtime/
  config/{launcher.example.json,launcher.json}
  logs/{<application>.log,launch-plan.json,snapshot-vulkan.json}
  profiles/26.4-snapshot-6.json
  launchers/{switchcraft-launcher-bridge,switchcraft-lwjgl-horizon}.jar
  runtimes/openjdk25/{lib/modules,conf,legal,...}
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
