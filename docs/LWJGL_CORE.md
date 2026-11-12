# LWJGL 3.4.3 core native provider

The core provider compiles original C from LWJGL commit
`30fac9b95f99cda97312232be25ba55297bf9951`. The source archive is fetched from
the pinned `source_url` in `dependencies.lock.json` and verified against
`source_archive_sha256` before extraction. The local cache is
`.deps/lwjgl_core_source.archive`.

`scripts/build-lwjgl-core.py` compiles the four portable main C sources
(`common_tools.c`, `MemoryUtil.c`, `ThreadLocalUtil.c`, and `Upcalls.c`) and
every C source directly under upstream `src/generated/c/` (portable JNI,
libc, and libffi bindings; OS-specific subdirectories are excluded). The
resulting 15-object provider contains actual JNI dispatch and table access,
memory helpers, `libc` string/stdio/locale/errno/stdlib calls, upstream thread
TLS, Java callback upcalls, and libffi CIF/closure bindings. Its resolver
inventory comes from defined global text or weak function symbols measured by
`nm`: 1,957 Java JNI exports plus genuine `JNI_OnLoad_lwjgl` and
`JNI_OnUnload_lwjgl` lifecycle exports. It does not infer exports from Java
declarations or flatten data symbols.

The static archive and generated resolver include are written to
`build/lwjgl-core/horizon/` (`liblwjgl-core.a` and `lwjgl_core_exports.inc`).
The resolver object is already in the archive. It uses the declarations in
`include/switchcraft/lwjgl_core.h`; named availability accepts only the exact
module `lwjgl`, while a `NULL` module lookup searches this provider in the
global native scope. Unsupported module names and absent exports return false
or address zero.

The Horizon build uses the repository's Java 25 runtime JNI headers, the
Horizon `jni_md.h`, the actual Java-switch SDK libffi 3.8 headers, and
devkitA64 ABI flags. `dependencies.lock.json` pins the corresponding libffi
3.8.0 source archive used by the host reference build. `FFI_DEFAULT_ABI` comes from that header; the build probes
its actual enum values before defining LWJGL's `HAS_FFI_*` compile constants.
It does not use LWJGL's bundled libffi header, which may describe a different
libffi ABI. The host reference builds the pinned genuine libffi 3.8.0 source
into a private static archive, then hides those archive symbols inside
`liblwjgl.so` so they cannot interpose on the JVM's own libffi. The Horizon
build does not define `LWJGL_LINUX` or another
desktop OS identity. Its Horizon-only
TLS branch uses libnx `threadTlsAlloc/Get/Set/Free`. The devkitA64 pthread
archive's dummy object does not provide the needed POSIX key hooks, while real
pthread implementations live in `libsysbase.a`; the selected libnx branch
avoids coupling this JNI lifecycle to either platform's pthread internals.
The pinned libnx archive defines all four `threadTls*` calls, and its
`threadExit` implementation invokes registered destructors for occupied
slots. LWJGL's `autoDetach` destructor is registered with `threadTlsAlloc`;
`JNI_OnLoad_lwjgl` returns `JNI_ERR` if slot allocation fails. The normal host
proof compiles upstream's actual Linux pthread branch.
`MemoryUtil`'s upstream unknown-platform page/cache query returns zero; Java's
upstream fallback supplies conservative page/cache values. The provider does
not include LWJGL dynamic shared-library loading or graphics/GLFW bindings.
Generated libc bindings call real platform C library functions; unsupported
functions are not replaced with success stubs.

One source patch changes upstream `JNI_OnLoad`'s return from JNI 1.6 to JNI
1.8 and selects the libnx TLS implementation on Horizon. The pinned Java 25 Horizon runtime implements JNI 1.8; this lets the
static provider expose the required `JNI_OnLoad_lwjgl` entry. The build renames
upstream `JNI_OnLoad` and `JNI_OnUnload` with compile-time symbol aliases and
preserves their implementation and TLS setup. The host reference build uses
the actual Linux configuration because it runs on Linux; the Horizon build
does not.

Build the Horizon archive with:

```sh
python3 scripts/build-lwjgl-core.py --cross
```

Build the same upstream JNI code as a host shared library and run a real
reference against the pinned LWJGL jar with:

```sh
python3 -m unittest discover -s tests -p 'test_lwjgl_core.py' -v
```

The reference checks named, wrong-module, and global lookups, then invokes the
resolved `JNI_OnLoad_lwjgl` with the running host JVM and verifies its JNI 1.8
return before invoking the real unload entry. It also calls
`MemoryUtil.nmemAlloc/nmemFree`, native memory writes and reads, libc
string/stdio/locale/errno JNI functions, JNI function-table access, libffi
version/default-ABI functions, and `JNI.invokeI` on an actual FFM upcall stub.
The Horizon build also
performs a relocatable AArch64 link check. Neither result establishes complete
LWJGL support or on-console behavior.

`tests/test_lwjgl_core_callbacks.py` exercises these upcalls through
Minecraft's cached LWJGL SDL 3.4.3 natives: an SDL timer thread calls a Java
`SDL_TimerCallback`, which logs through SDL's native `SDL_LogOutputFunction`
closure. This covers a genuine foreign-thread JNI attach and nested Java
callbacks through libffi. It is host-only evidence. Run both references with:

```sh
python3 -m unittest tests.test_lwjgl_core tests.test_lwjgl_core_callbacks -v
```
