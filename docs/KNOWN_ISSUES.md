# Known issues

* **Horizon Java 25 is absent. Minecraft title on Switch is NOT ACHIEVED.** The
  verified Demo title is a Linux/llvmpipe reference only. No physical Switch is
  attached; every native CPU/input/SD/graphics/runtime test is NOT TESTED.
* OpenJDK 25 fails configuration at unsupported OS elf. A real OS/platform and
  class-library port is needed: virtual memory, exceptions/safepoints, TLS and
  threads, static natives/symbols, filesystem/network and runtime image.
* The JNI adapter executes Java 25 JNI/FFM tests on host and reports unavailable
  on Horizon. miniJVM is Java 8 only. No classfile-69/modern Minecraft support is
  inferred from Java 8 class-loading or reflection tests.
* libffi AAPCS64 and libnx RW/RX upcall code compile/link, but hardware permissions,
  cache behavior, closure execution and teardown still need physical testing.
  Failure returns actual libnx errors; no patches or overclocking are attempted.
* NVK remains experimental/nonconformant on integrated Maxwell. Base-feature
  success does not prove shader/presentation stability or complete game support.
  The prebuilt archive does not identify its exact historical nxvk source commit.
* SDL3/VI swapchain and gamepad paths are implemented and linked, with OpenGL/EGL
  disabled. They are hardware untested. Driver calls may hang; fences have finite
  timeouts, but queue/device idle calls may still block. No GPU reset guarantee.
* Per-image present semaphores avoid reusing a presentation wait too early. The
  baseline is deliberately serialized and not a performance benchmark. Offscreen
  triangle coverage and presentation coverage are separate NRO tests.
* Shaderc, VMA, SPIR-V Cross, FreeType, audio and static LWJGL loading into a real
  Horizon JVM are not integrated. Native SDL3 alone does not implement Java FFM.
* Strict Vulkan uses a Java 25 instrumentation/Class-File-API bridge. Those runtime
  modules/services are unavailable on Horizon. It refuses unrecognized class
  hashes and changes only renderer selection, without account/authentication changes.
* Fabric/Mixin, arbitrary Mods, authentication and network/audio integration are
  not implemented. The linked native networking/TLS code is not verified.
* Metadata is bounded to 4 MiB/512 versions/16 inheritance levels. OS-version
  regex and Maven @extension cases are limited. Assets are counted/planned, not
  exhaustively checked by the console inspector. Official default-user-jvm flags
  are recorded but not applied blindly to the Switch memory budget.
* Heap settings do not cap all native memory. Usable process/malloc memory must
  be measured in application-mode hbmenu; 4 GB physical RAM is not Java heap.
* NRO chaining requires next-load support and the packaged SD layout. Launch
  individual NROs directly if chaining is unsupported. SD logs have no rotation;
  crash recovery is HOME/relaunch and matching ELF symbolication.
* Legacy OpenGL artifacts remain on branch 1.12.2 and are excluded from main's
  package. AOT is still blocked on missing external runtime/game build inputs.
* Docker/CI are supplied but not independently executed here. Private cross-repo
  CI checkout needs a read token configured in GitHub; local authenticated builds
  do not need it embedded in source.
