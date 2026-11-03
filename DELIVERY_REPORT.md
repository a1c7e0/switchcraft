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

Source `e08f36a9d19cf461312f87a866f9bb1f39d57d98`, Java source `b7c2ac7fd422bc2543e5c698db4e33a01cc0312d`, dirty `False`.
Paths are relative to `/workspace/switchcraft/dist`.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `switch-diagnostics.nro` | 248005 | `fd0922df232f38f19c4bdd85dab20ddb51db973010328b011522b6f29bc76008` |
| `vulkan-test.nro` | 11995333 | `e282e61d16d9430521d6ab7dfcd9332793d2bb32dc32b83d947f068d2fb2fa39` |
| `vulkan-present.nro` | 12679365 | `459028b76bfa108812226a750ee74fdffffd33e72a4e59779415b2d2cf7b8ab0` |
| `minecraft-launcher.nro` | 1870021 | `b5d0c6a8f8fb54f4bb326b37193bfaf676bc727e5bc5d6f2f774600d2ff9146d` |
| `java-test.nro` | 1165509 | `51a2d28174d98b2e6e0b8242a616aba66a3ee30464b95e5261daa386b4cef6f9` |
| `ffi-test.nro` | 256197 | `a0648247ecaa82e4d674ed18396d30754b0b1f53e7c6f7155bae20c783dc7df4` |
| `zero-services-test.nro` | 317637 | `25061d17f56545efda7a242e5a56e187d815517fa4910d82fcdd8f7bf56c15df` |
| `java25-test.nro` | 6944965 | `ac93dbfb4c99b6f666fdd6cb95bc0c16b7964e8c28ee4d26095bfb0c8f788375` |
| `switchcraft-java25.nro` | 19237061 | `4cdd69eb1c0f1879f2696cfb6827359efa3cdf66b57a7ac1470af146bf3f1d24` |
| `switch-minecraft-test-package.zip` | 149934330 | `72e4e363a6c1414bca87f0501fe6d89a5e719fabaf0a776204ceceddf0876ddd` |
| `switchcraft-corresponding-source.tar.gz` | 124356875 | `a5ad9ce18e27c831f64a380cdf3f775e86900d9c4cd6bec0a0c4ae8d2ad09e3b` |
| `switchcraft-debug-symbols.zip` | 39747317 | `712b6f7d048bb84fb44acb7f1a4027c027c6544cf8fe05feb79e0b35a0144817` |
| `switchcraft-native-sdk.tar.gz` | 41151 | `ee3f46fa124fff46b1e2f3b9d940563b995e653d9863faf69930aca69d168460` |

## C. Build validation

Nine genuine NROs have matching AArch64 ELFs, NRO0/ASET/NACP/icons/build IDs.
Host tests cover metadata, fake/truncated artifact rejection, feature gates,
feedback allowlisting, native lookup and a synthetic renderer transformation.
When SWITCHCRAFT_CLIENT_JAR is supplied, its SHA-1 and renderer-class SHA-256
are verified and the actual class transformation is checked. Independent runtime
tests execute Java 8 JARs and Java 25 standard JNI/FFM/options on the host.
See build/host-tests.log and build/java-runtime.log for exact results.

## D. Hardware

All Horizon execution is NOT TESTED. Java 25 VM is cross-linked in diagnostics,
but startup and Java execution have not been verified. The Switch
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

Horizon JVM 25 execution, static LWJGL/native module loading,
shaderc/VMA/SPIR-V Cross/audio integration and device instrumentation remain open.
See docs/JAVA_INTEGRATION_HANDOFF.md and docs/NATIVE_BINDINGS.md for the exact
SDK boundary, currently linked symbols and integration requests.
Base Vulkan feature success alone does not establish game compatibility. Fabric
and arbitrary Mods are not supported. NVK remains experimental on Maxwell.

## I. Next steps

Return native SDL/VI/feature and Java25 A/X/Y/combined Hello logs; resolve actual
device failures with the independent Java task, then complete static LWJGL/FFM
and other native bindings before trying the pinned title on the console.

## J. Source and commits

The legacy baseline is preserved on branch legacy/1.12.2. main removes OpenGL and local
Java implementation ownership, pins java-switch and SDL3, and packages explicit
source/dependency/runtime/hardware evidence. Documents are English.

```
e08f36a Update Java runtime pin to upstream build fixes
5d24c6e fix: verify all unpacked SDK and runtime files against archives
58a5666 docs: add Java to SDL FFM device test
1c22d99 feat: add Java JNI FFM smoke through real SDL symbol
4e73a68 docs: describe Java 25 integration evidence and hardware workflow
e7fce97 feat: cross-link instrumented Java 25 with SDL Vulkan resolver
c63ed3d feat: compose JDK and Switchcraft native resolver providers
4f4544a build: pin instrument-enabled Horizon Java runtime revision
7ce851b fix: avoid GPU teardown after a failed fence wait
f194b6f docs: clarify tester collection and delivery scope
c4e3fcc test: verify strict Vulkan transform against pinned client
d20663d docs: establish Java SDK handoff and baseline evidence
```
