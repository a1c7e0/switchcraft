# Native shader libraries

Switchcraft's Horizon shader provider is a static AArch64 build of the C APIs
that LWJGL 3.4.3 uses from Shaderc and SPIRV-Cross. It supports the exact
provider module names `shaderc` and `spirv-cross-c`. The resolver's export list
is generated from the linked upstream archives and contains only defined
function symbols (`T` or `W` in the target `nm` output); a nonzero lookup is an
address of the implementation linked into this build, not a placeholder or a
data address.

`scripts/build-shader-libraries.py` is the source-build entry point. It uses
immutable source revisions and verified archive SHA-256 digests from
`dependencies.lock.json`, applies only the maintained Horizon portability
patches, and builds host executables with the host compiler. Cross compilation
uses devkitA64 and libnx for AArch64 Horizon; it must not define Linux ABI
macros or substitute a desktop binary. The resulting static archives and
link-proof objects belong in `build/`, not in shipped runtime data. The source
and license notices for all included projects are kept with this repository.

The host validation compiles a small GLSL vertex shader with the real
`shaderc_compile_into_spv` API, then parses the resulting SPIR-V and inspects
its stage-input reflection using SPIRV-Cross's real C API. This establishes
that both upstream libraries are functional and mutually compatible in the
host build. Cross link proof establishes that the AArch64 objects and provider
resolve together. Neither check establishes execution on Switch hardware.

The Shaderc patch serializes its GLSL compile and assembly entry points with a
recursive libnx mutex. This protects glslang shared process state while allowing
callback reentry. C++ TLS stays enabled and is supplied by the Horizon thread
runtime. POSIX mutex and once calls use devkitPro's real `libsysbase` pthread
implementation, backed by libnx; the empty `libpthread.a` and local pthread
substitutes are excluded. The cross link check produces a no-undefined target
ELF and verifies the linker map selects `libsysbase` and the libnx TLS path. A
Switch run must still confirm shader compilation and reflection before on-device
execution is claimed.
