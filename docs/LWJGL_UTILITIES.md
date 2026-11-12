# LWJGL STB and VMA native providers

The utility provider builds from the already pinned LWJGL source cache at
`.deps/lwjgl-core-source/lwjgl3-30fac9b95f99cda97312232be25ba55297bf9951`.
The builder only reads this tree and verifies its prepared source archive pin
against `dependencies.lock.json`.

`scripts/build-lwjgl-utilities.py` compiles every generated STB JNI C file and
both generated VMA C++ files. The VMA file contains the original full
`vk_mem_alloc.h` implementation. AArch64 Horizon output is the static archive
`build/lwjgl-utilities/horizon/liblwjgl-utilities.a`; its generated export
inventory and resolver object are included. The host reference modules and
inventory are under `build/lwjgl-utilities/host/`.

The resolver provides exactly `lwjgl_stb` and `lwjgl_vma` by name; `NULL`
lookup searches both modules as the global native scope. Names are derived
from global text/weak function symbols in the built objects. It exports 224
STB Java JNI methods and 73 VMA Java JNI methods, plus one JNI 1.8 load hook
for each module. The hooks check JNI 1.8 with the supplied JavaVM; they do not
pretend to perform module setup. Static VMA global allocation function
pointers are namespaced at compile time to preserve the module-local globals
that separate upstream desktop libraries get from separate shared objects.

The pinned jars contain 299 Java native method declarations. All except two
match the built native table. VMA's
`nvmaGetMemoryWin32Handle` and `nvmaGetMemoryWin32Handle2` methods are guarded
by upstream `LWJGL_WINDOWS` source blocks and are not built for Horizon.
No Linux OS macro is defined for the Horizon objects. VMA is compiled with
`VMA_STATIC_VULKAN_FUNCTIONS=0` and `VMA_DYNAMIC_VULKAN_FUNCTIONS=0`; callers
must populate `VmaAllocatorCreateInfo.pVulkanFunctions` with actual Vulkan
function addresses from the active loader/driver. The objects have no direct
Vulkan entry-point imports. This lets the NVK path dispatch through its
provided Vulkan functions. No OpenGL, EGL, X11, or Win32 platform APIs are
introduced.

Host references use the official Minecraft metadata-pinned LWJGL 3.4.3 STB,
VMA, and Vulkan Java jars. They call STB PNG decoding and easy-font packing,
and create/destroy a VMA allocator using SwiftShader through the host Vulkan
loader. The test also compares every Java native declaration with the
generated export inventory and exercises exact module/global resolver
lookups and both JNI 1.8 load hooks. These are host results only.

Build the Horizon archive and relocatable link proof with:

```sh
python3 scripts/build-lwjgl-utilities.py --cross
```

Run the host reference with:

```sh
python3 -m unittest discover -s tests -p 'test_lwjgl_utilities.py' -v
```

For final packaging, preserve the upstream LWJGL BSD-3-Clause notice, the
VMA `vma_license.txt` notice, and the per-header STB notices. The repository
already carries the STB TrueType notice at `licenses/STB-TRUETYPE.txt`.
Neither a cross-link nor these host references establish Horizon runtime or
device execution.
