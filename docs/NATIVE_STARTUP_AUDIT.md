# Snapshot 6 native startup audit

This audit traces optional native and system information paths in the official
`26.4-snapshot-6` client. The game client and its manifest libraries were
downloaded to `/tmp/r4-mc-reference` for inspection and are not checked in.
Input identities and the static module scan are recorded in
[`minecraft-r4-module-audit/reference.txt`](evidence/minecraft-r4-module-audit/reference.txt)
and [`jdeps-manifest-classpath-modules.txt`](evidence/minecraft-r4-module-audit/jdeps-manifest-classpath-modules.txt).
The client SHA-256 is
`09d7e86508eb8b01c8e6ecc268ac1e4f8b9f0153c8fcff3201bf3f170199ca8b`.

## Reachability from `Main.main`

`net.minecraft.client.main.Main.main` calls `com.mojang.jtracy.TracyBootstrap.setup`
at bytecode offset 684 only when the parsed `--tracy` option is present (branch
at offsets 674–681). It calls `TracyClient.reportAppInfo` unconditionally at
offset 738, but that method checks the static `loaded` flag and returns without
calling `TracyBindings.appInfo` when Tracy was not loaded. Thus the ordinary
startup path does not establish a Tracy native-load requirement. The optional
JFR path is also guarded by its profile option. In addition,
`net.minecraft.util.profiling.jfr.JvmProfiler`'s static initializer checks
whether its module layer contains `jdk.jfr`; when absent it creates the game's
`NoOpProfiler` implementation and only calls `FlightRecorder.isAvailable()`
when the module is present. Thus the reduced image's missing JFR module has an
explicit game fallback for the default profile. See
[`javap-main-entry.txt`](evidence/minecraft-r4-module-audit/javap-main-entry.txt)
for the main entrypoint; [`javap-jvmprofiler.txt`](evidence/minecraft-r4-module-audit/javap-jvmprofiler.txt) records the profiler fallback bytecode.

`Main.main` calls `CrashReport.preload` at offset 749. `CrashReport.preload`
allocates the reserve and constructs a crash report; `CrashReport` constructs a
`SystemReport`. That report calls OSHI for hardware and software details through
`ignoreErrors`. The helper catches `Throwable`, logs the failed group, and adds
an error entry instead of propagating it. OSHI's `SystemInfoFactory.create`
selects among providers registered by service metadata: the selected manifest
contains `oshi-core-ffm`'s `oshi.ffm.SystemInfo` and `oshi-common`'s
`oshi.nativefree.SystemInfo`. The factory tries available providers and catches
`ServiceConfigurationError` and `RuntimeException`; no usable provider can
still raise `IllegalStateException`, but the enclosing report helper catches
that failure as well. The FFM provider reports priority 20 and the native-free
provider priority 0, so FFM wins when it reports available; the native-free
provider is also present in the official manifest. The relevant service
declarations are in the official JARs, not a repository-native shim.

LWJGL's allocator selection is another guarded optional native path. Its
`MemoryUtil.LazyInit` calls `MemoryManage.getInstance`. The latter tries the
configured allocator candidates using reflection and catches `Throwable` for
each failed candidate, then returns `MemoryManage.StdlibAllocator` if none can
be instantiated. This is the fallback observed in `MemoryManage.getInstance`
bytecode. The prior Linux launch log selecting jemalloc is host evidence of
that environment's allocator choice; it does not make jemalloc a hard title
startup dependency.

## Networking transports

The client has an explicit availability fallback in
`net.minecraft.server.network.EventLoopGroupHolder.remote(boolean)`: when the
argument is true it tries `KQueue.isAvailable()`, then `Epoll.isAvailable()`,
then returns the NIO holder. When false it returns NIO directly. This method
is used to choose a remote network event loop; it is not part of `Main.main`
startup. On Horizon, unavailable epoll/kqueue native transports therefore do
not by themselves block reaching the title through the normal networking
selection path. Multiplayer sockets and TLS remain separate functional work;
this audit does not claim they work on Horizon.

## Findings and limits

- This audit found no additional unconditional native-load blocker in the
  Tracy, jemalloc allocator-selection, OSHI system-report, or Netty optional
  transport paths above.
- `jdeps` lists additional absent JDK modules from full client and library
  contents. Those class references do not prove eager loading. In particular,
  do not treat optional JFR, audio, networking, or reporting code as a title
  startup blocker solely from its presence in a JAR.
- The graphics path remains distinct: SDL window/event/input functionality and
  Vulkan/VMA renderer services are real native integration requirements for
  this project. Cross-built symbols or host tests do not prove Horizon runtime
  behavior; see [`LWJGL_CORE.md`](LWJGL_CORE.md),
  [`LWJGL_HORIZON_COMPAT.md`](LWJGL_HORIZON_COMPAT.md), and
  [`NATIVE_BINDINGS.md`](NATIVE_BINDINGS.md).
- The official manifest does not select an LWJGL tinyfd artifact. No tinyfd
  startup dependency was found.
- These are static bytecode and manifest findings, not a new launch result.
  The official title has only the separately documented Linux host evidence;
  Horizon startup and native runtime behavior remain unverified by this audit.

Reproduce the bytecode inspection with JDK 25 `javap -c -p` against the client
and the manifest-derived classpath recorded in
[`reference.txt`](evidence/minecraft-r4-module-audit/reference.txt). Do not
infer eager class initialization from a constant-pool reference or a method
that is reachable only after a user action.
