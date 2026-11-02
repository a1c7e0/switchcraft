# Snapshot 6 delivery report

## A. Implemented

Mainline targets 26.4-snapshot-6 and Vulkan. SDL3/VI swapchain and gamepad probe,
exact base-feature profile, NVK offscreen tests, read-only launch planning and a
hash-pinned Vulkan-only class transformation exist. Java is owned by the separate
java-switch repository and consumed at a fixed commit. A limited static SDL/Vulkan
symbol lookup is linked into the presentation probe; it is not a Java loader.
Session/stage diagnostics, an allowlisted feedback collector and matching debug
ELFs are included. Physical execution remains NOT TESTED.

## B. Artifacts

Source `7ce851b3c4fca4f85a6fee64fd9b0a40ef5d2255`, Java source `9f6ac4efc04a1750fe54c62d72c4401fda89e68a`, dirty `False`.
Paths are relative to `/workspace/switchcraft/dist`.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `switch-diagnostics.nro` | 248005 | `84f9cfc6bef7b1d5f66afa7ba6e7456bc437c1edfee4ba07e3280c07aa7b912c` |
| `vulkan-test.nro` | 11995333 | `9c147968c7dd02376880682356d5c0a366f3e8b7cc8bcd097a67d22c3dd588a0` |
| `vulkan-present.nro` | 12679365 | `4765e70267a55272cad5104548fcf1c74738bcd93506cb1ae645321373d1c923` |
| `minecraft-launcher.nro` | 1870021 | `44ea5d0201a48e6aa11bc55c9bad75a8e79af156d444589ea4156739d6060b9d` |
| `java-test.nro` | 1165509 | `7c5bb4b3c394dad2bdc95c520466153c1eef913289ff39380ab73c84f2e440d4` |
| `ffi-test.nro` | 252101 | `52bdba06d624df4e20b6842971e4acc1723abb66903aac1aa73d1302888c321b` |
| `switch-minecraft-test-package.zip` | 16019033 | `ab511e7726bb8cd437c93f8fcb26f1ae657c9fa158fc0a9890a52c0fad738aad` |
| `switchcraft-corresponding-source.tar.gz` | 7404354 | `ee610b7af1643d707914deb122d3e502a6a3340a2a3631a5347b15d0cb5576f8` |
| `switchcraft-debug-symbols.zip` | 20958569 | `821e72f3fc94f627fe9fb04d67399ab0680be000e72726c8621a6af905842cd9` |
| `switchcraft-native-sdk.tar.gz` | 24723 | `0625b604aaa6aec2b10afbef163a281227d2d007f9d27f6d226a42833d9c424b` |

## C. Build validation

Six genuine NROs have matching AArch64 ELFs, NRO0/ASET/NACP/icons/build IDs.
Host tests cover metadata, fake/truncated artifact rejection, feature gates,
feedback allowlisting, native lookup and a synthetic renderer transformation.
When SWITCHCRAFT_CLIENT_JAR is supplied, its SHA-1 and renderer-class SHA-256
are verified and the actual class transformation is checked. Independent runtime
tests execute Java 8 JARs and Java 25 standard JNI/FFM/options on the host.
See build/host-tests.log and build/java-runtime.log for exact results.

## D. Hardware

All Horizon execution is NOT TESTED. Java 25 VM is not built/linked. The Switch
Minecraft title objective is NOT ACHIEVED. The Linux Java 25 llvmpipe Vulkan Demo
reference did reach the title screen, including the strict Vulkan transformation;
its screenshot and logs are explicitly labeled HOST ONLY.

## E. Installation

Merge COPY_TO_SD or the install ZIP onto the SD root, preserve saves/configuration,
and use application-mode hbmenu. No game files or real launcher.json are included.
Import an owned installation's versions/libraries/assets if testing the inspector.

## F. First three hardware sessions

1. Native menu, memory, SD and threads in switch-diagnostics.
2. vulkan-present A for exact feature capture, then X for SDL3/VI/gamepad.
3. vulkan-test transfer/offscreen rendering, then ffi-test downcall/W^X tests.
The Java 8 suite is separate; it is not Java 25 compatibility. Export mc-runtime/logs.
The packaged collect-feedback.py creates a new archive of allowlisted logs and
the manifest. Review it and any separately attached crash reports before sharing.

## G. Architecture

See docs/ARCHITECTURE.md and docs/architecture.svg. Java source/build boundaries
and unavailable VM state are explicit; no Linux runtime is bundled for Horizon.

## H. Limits

Horizon JVM 25, class-library OS services, static LWJGL/native module loading,
shaderc/VMA/SPIR-V Cross/audio integration and Java instrumentation remain open.
See docs/JAVA_INTEGRATION_HANDOFF.md and docs/NATIVE_BINDINGS.md for the exact
SDK boundary, currently linked symbols and integration requests.
Base Vulkan feature success alone does not establish game compatibility. Fabric
and arbitrary Mods are not supported. NVK remains experimental on Maxwell.

## I. Next steps

Return native SDL/VI/feature and FFI closure logs; finish the Horizon OpenJDK 25
OS layer (Zero plus libffi fallback linker first), then static JNI/FFM library
loading and LWJGL bindings. Re-run the same pinned title test on the console.

## J. Source and commits

The legacy baseline is preserved on branch legacy/1.12.2. main removes OpenGL and local
Java implementation ownership, pins java-switch and SDL3, and packages explicit
source/dependency/runtime/hardware evidence. Documents are English.

```
7ce851b fix: avoid GPU teardown after a failed fence wait
f194b6f docs: clarify tester collection and delivery scope
c4e3fcc test: verify strict Vulkan transform against pinned client
d20663d docs: establish Java SDK handoff and baseline evidence
124a7fa feat: package safe tester feedback and matching debug symbols
8c067ad feat: add native symbol lookup and detailed Vulkan stage diagnostics
f93bfc0 feat: integrate Horizon virtual memory diagnostic
2295bce docs: reflect main as the default branch
483e23a build: pin Java runtime FFI lifecycle fix
7648f7c docs: preserve legacy branch and describe temporary default mirror
53e1e6c test: reproduce snapshot 6 Vulkan-only title with final reference script
0047e09 docs: publish honest snapshot-6 architecture build hardware plan and delivery packaging
```
