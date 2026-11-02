# Snapshot-6 native binding status

Snapshot metadata lists LWJGL core, SDL, Vulkan, VMA, shaderc, SPIR-V Cross,
FreeType, OpenAL, STB, jemalloc and OpenGL. The strict renderer transformation
selects Vulkan only; the OpenGL metadata entry remains part of the official
client. The SDL3/VI executable is native code, not an LWJGL implementation.

`build/libswitchcraft-native.a` contains an AArch64, exact-name allowlist lookup.
The current table covers SDL initialization/teardown, errors, windows, event and
gamepad enumeration/open/close, SDL Vulkan extensions/surface, and Vulkan
`vkGetInstanceProcAddr`. The `vulkan-present` NRO links and calls the table;
unknown names return NULL. `scripts/verify-native-link.py` verifies actual linked
symbols and checks that GL/EGL entry points are absent. A host test invokes a
function found by a synthetic table and verifies missing-name behavior. This is
not a Java lookup implementation, dynamic loader, full SDL API, or ABI proof
for arbitrary signatures. Resolve Vulkan device functions through the driver.

Native WSI uses pinned etonedemid/SDL, zlib license, plus Mesa NVK and libnx;
revisions and archive hashes are in dependencies.lock.json. No new Vulkan driver
is implemented here. VMA, shaderc, SPIR-V Cross, FreeType, OpenAL, STB, jemalloc,
LWJGL core native/FFM marshalling and Java static-library registration have not
been integrated into a Horizon JVM. That work remains blocked on actual runtime
interfaces and dependencies. No claim of Joy-Con gameplay is made.
