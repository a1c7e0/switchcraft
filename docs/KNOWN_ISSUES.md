# Known issues and boundaries

* **All Switch hardware functionality is NOT TESTED.** Cross-compilation proves
  format/link compatibility only. Atmosphère/libnx/driver behavior needs real hardware.
* Minecraft is not playable. The inspector never starts a game. The independent
  host 1.12.2 experiment fails in LWJGL initialization before a title screen.
* OpenJDK 8 has partial upstream Horizon changes, but its runner, POSIX layer,
  runtime image, signal/exception handling and build recipe are incomplete here.
  No OpenJDK 17/21/25 port is implemented.
* miniJVM is an experimental Java 8 diagnostic. It has a custom native interface,
  not standard JNI Invocation. No desktop native `.so` can be loaded. JIT,
  subprocesses, Immix memory mapping, AWT and LWJGL are unavailable.
* The Java diagnostic's 64 MiB heap value is a collector target, not a hard cap
  over native metadata, stacks or libraries. It runs once per process. An
  unbounded user JAR can hang or exhaust memory; plus cannot interrupt an active
  synchronous Java call. Use the HOME menu/relaunch for recovery.
* Vulkan uses a nonconformant Maxwell NVK build whose constructor opts into
  Mesa's experimental GPU exposure. No Vulkan feature level is assumed until
  recorded on hardware. Instance API requests 1.0; reported device version is
  logged separately. WSI/surface/swapchain presentation is not implemented.
* Vulkan triangle rendering is offscreen RGBA8 with center/corner readback and
  a console ASCII preview. It is not visible Vulkan swapchain presentation.
* GPU commands use a five-second fence timeout. A kernel/driver call itself may
  still hang. On fence timeout the application exits without destroying pending
  resources; there is no verified GPU reset/recovery path.
* OpenGL uses devkitPro Mesa 20.1.0 NVC0, separate from NVK's Mesa 25.0.7. The
  console renderer is released during EGL rendering. Restoration/lifecycle and
  repeated driver initialization need hardware testing.
* Zink, OpenAL audio, networking tests, touch, remapping, performance tuning and
  Fabric/Mixin are unimplemented. Linked networking/TLS code is not validated.
* The launcher reads bounded JSON (4 MiB), limits scans to 512 versions and
  inheritance to 16 levels. Maven `@extension` and OS-version regex rules are
  not implemented. Asset object counts are inspected; object hashes/downloads
  are not exhaustively verified. Rules target Horizon/aarch64, not Linux.
* The generated classpath uses `;` because libnx SD paths contain `:`. A future
  JVM backend must use the same separator or translate paths; Linux classpaths
  cannot be copied blindly.
* Metadata heap/JVM/game arguments are plans, not executed commands. Authentication
  placeholders remain unresolved. There is no account authentication or bypass.
* SD logs append and flush synchronously; there is no automatic log rotation or
  crash dump handler. Driver crashes may lose the last message. SD failure is
  shown on screen; an existing diagnostic temporary file is preserved.
* NRO chaining depends on Homebrew Menu's next-load support and the packaged
  absolute layout. Direct launch of each NRO remains available if chaining fails.
* AOT cannot be reproduced from the inspected repository alone: external
  `pz-switch`, musl-nx, GraalVM output and user-supplied patched JAR inputs are
  missing. Its script requests 24 GiB host heap, beyond this executor's RAM.
* CI/Docker definitions are supplied; only the local pinned-toolchain path was
  executed. The NVK archive is hash-pinned, but upstream did not record the exact
  nxvk commit used for that binary. Driver-source rebuild provenance remains open.
