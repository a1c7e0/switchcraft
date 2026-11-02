# Snapshot 6 delivery report

## A. Implemented

Mainline targets 26.4-snapshot-6 and Vulkan. SDL3/VI swapchain and gamepad probe,
exact base-feature profile, NVK offscreen tests, read-only launch planning and a
hash-pinned Vulkan-only class transformation exist. Java is owned by the separate
java-switch repository and consumed at a fixed commit.

## B. Artifacts

Source `f93bfc005cddb77a1f4ddc44d1b14d67d6a2797d`, Java source `9f6ac4efc04a1750fe54c62d72c4401fda89e68a`, dirty `False`.
Paths are relative to `/workspace/switchcraft/dist`.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `switch-diagnostics.nro` | 248005 | `3dd38e24cb95f697dbe4104a9611a4b8467adfb17656a37d91075a18b8de3736` |
| `vulkan-test.nro` | 11995333 | `679b2e6d27bb6b8d012be9f86dfb70b79fd97cacdc5f3b823bc05494b07d4043` |
| `vulkan-present.nro` | 12675269 | `176620f41383684b95c95c6c0e215ed12779876c4c8f0979973e8fa9743ae68d` |
| `minecraft-launcher.nro` | 1870021 | `d6de884f879f8eab37842e72086af562e85ec8f1a4900e5808be440539d0d5e4` |
| `java-test.nro` | 1165509 | `7c5bb4b3c394dad2bdc95c520466153c1eef913289ff39380ab73c84f2e440d4` |
| `ffi-test.nro` | 252101 | `52bdba06d624df4e20b6842971e4acc1723abb66903aac1aa73d1302888c321b` |
| `switch-minecraft-test-package.zip` | 16004691 | `89d0b2ea56ad0253885c20c9bfcf50d0e0dcdbb65031e37ac24327ed6d87c5c3` |
| `switchcraft-corresponding-source.tar.gz` | 7394111 | `98c67d8df132cc45611b858f74eb4de1dcca2366ad0fe9972cb5d015c05bde29` |

## C. Build validation

Six genuine NROs have matching AArch64 ELFs, NRO0/ASET/NACP/icons/build IDs.
Host tests cover metadata, fake/truncated artifact rejection, feature gates and
a synthetic executable renderer transformation. Independent runtime tests execute
Java 8 JARs and Java 25 standard JNI/FFM downcall/upcall/structured JVM options.
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

## G. Architecture

See docs/ARCHITECTURE.md and docs/architecture.svg. Java source/build boundaries
and unavailable VM state are explicit; no Linux runtime is bundled for Horizon.

## H. Limits

Horizon JVM 25, class-library OS services, static LWJGL/native module loading,
shaderc/VMA/SPIR-V Cross/audio integration and Java instrumentation remain open.
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
f93bfc0 feat: integrate Horizon virtual memory diagnostic
2295bce docs: reflect main as the default branch
483e23a build: pin Java runtime FFI lifecycle fix
7648f7c docs: preserve legacy branch and describe temporary default mirror
53e1e6c test: reproduce snapshot 6 Vulkan-only title with final reference script
0047e09 docs: publish honest snapshot-6 architecture build hardware plan and delivery packaging
074063f refactor: consume pinned java-switch SDK and enforce Vulkan-only snapshot launch
6cc6ef8 feat: target snapshot 6 with SDL3 Vulkan-only WSI and exact feature profile
feb2f4d fix: force memory test accesses and generate complete artifact delivery report
60f58b0 build: package verified SD release with source licenses and hardware test plan
e24744a feat: integrate interpreter-only miniJVM with real Java JAR diagnostics
9055051 feat: inspect Minecraft installations and verify genuine NRO artifacts
```
