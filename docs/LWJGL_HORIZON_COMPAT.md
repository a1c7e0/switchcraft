# LWJGL 3.4.3 Horizon compatibility

Switchcraft targets the LWJGL 3.4.3 classes used by Minecraft 26.4-snapshot-6.
The original JARs remain intact; `build/switchcraft-lwjgl-horizon.jar` is placed
before them on the game classpath. Java sources derive from upstream commit
`30fac9b95f99cda97312232be25ba55297bf9951` and retain the LWJGL BSD license.
The build verifies the official core, Vulkan, OpenAL, OpenGL, and JSpecify JAR hashes
from `dependencies.lock.json` before compiling overrides.

The pinned upstream source checksums are recorded in `dependencies.lock.json`
for `Platform.java` and `Library.java`. The unmodified source SHA-256 values for
the additional copied `Configuration.java`, Vulkan `VK.java`, and OpenAL
`ALC.java` are, respectively, `bb811e86c859b4d6f79fbbc32084003d73fe1b64fb4bfffeb6b695c25c6de259`,
`7f3002cafab9c2443c978581866ef52cf62d366ced84b0432a02e32b3603b1ec`, and
`975a6140209f15e382790cc9cbfa743c754e586623d9a03353a3fbd3af021e41`.

## Platform and library policy

`Platform` identifies Horizon directly and keeps its ARM64 architecture. It
does not select Linux library paths. `Library.loadNative` uses an exact alias
table to resolve process-owned static modules through Switchcraft's
`NativeSymbols` JNI bridge:

| LWJGL module | LWJGL library name | Static resolver module |
| --- | --- | --- |
| `org.lwjgl.sdl` | `SDL3` | `SDL3` |
| `org.lwjgl.vulkan` | `libvulkan.so.1` | `vulkan` |
| `org.lwjgl.freetype` | `freetype` | `freetype` |
| `org.lwjgl.openal` | `openal` | `openal` |
| `org.lwjgl.shaderc` | `shaderc` | `shaderc` |
| `org.lwjgl.spvc` | `spirv-cross` | `spirv-cross-c` |

These names are the pinned 3.4.3 caller names; module availability and each
symbol address still come from the real composed resolver. Unknown module/name
pairs throw `UnsatisfiedLinkError`. Missing symbols return address zero. The
adapter does not manufacture a shared-library handle or filesystem path, and
`free()` cannot unload process-owned code. Vulkan exposes only
`vkGetInstanceProcAddr` globally; device and instance functions remain under
Vulkan's normal dispatch.

The LWJGL static initializer still delegates JNI library loading to
`System.loadLibrary`, so a missing static JNI provider fails normally. This
adapter does not replace LWJGL's generated JNI call implementations.

The upstream `Configuration` class is preserved with a narrow Horizon policy:
`OPENGL_EXPLICIT_INIT` defaults to true only when `os.name` is `Horizon` and the
user has not set `org.lwjgl.opengl.explicitInit`. An explicit true or false
property wins. The default reads `os.name` directly to avoid a class-initializer
cycle through `Platform`. The copied `GL.java` also skips its unconditional JNI
library load in that Horizon explicit-init case; the upstream flag alone would
not avoid that load. This lets strict-Vulkan applications load incidental
OpenGL Java classes without automatically loading a GLX or OpenGL driver; it
does not make OpenGL available. An explicit OpenGL initialization request
reaches an honest `UnsupportedOperationException` instead of a fabricated
provider. EGL, OSMesa, and OpenGL ES default library selection also reports
unsupported on Horizon.

The pinned Vulkan `VK.create()` and OpenAL `ALC.create()` platform switches
include Horizon and pass their official names to the same exact static adapter.
This is load routing only; successful audio or Vulkan behavior requires the
corresponding real module and exported functions in the composed resolver.

## SDL exports

`scripts/generate-sdl-symbols.py` produces `build/sdl_symbols_generated.h` by
preprocessing public SDL headers with the target compiler and `__SWITCH__`,
then intersecting the active `SDL_DECLSPEC`/`SDLCALL` function declarations
with global function definitions (`T`/`W`) in the built
`.deps/sdl3/lib/libSDL3.a`. The generated manifest records input and output
hashes, selected headers, counts, and unavailable declarations. At the current
pinned build, the Switch target exposes 1,242 such names. Functions absent from
the archive or inactive for Switch are not entered in the resolver table.

The native table resolves exact SDL3 function addresses. It does not provide
signature metadata; LWJGL's generated FFM bindings supply call signatures.
Vulkan's global table entry remains only `vkGetInstanceProcAddr`, so
device-specific Vulkan functions are never flattened into the global resolver.
The generated table establishes addresses for archive members, not runtime
subsystem success or a physical-console result.

## Evidence and limits

`tests/test_lwjgl_horizon.py` uses the real pinned LWJGL classes and host JNI
fixtures to call `SDL_GetVersion` via Java FFM, verify exact aliases, exercise
missing module/symbol handling, and confirm process-lifetime ownership. It also
checks the Horizon OpenGL explicit-init default and explicit override.
`tests/test_sdl_exports.py` checks declaration/archive intersection against a
fixture and regenerates the table with the pinned AArch64 Switch compiler.
These host/build checks do not establish Horizon execution, complete SDL
subsystem behavior, OpenAL device output, or Minecraft reaching its title.
