# R5 device retest package

Published release:
[`test-suite-2026-11-13-r5`](https://github.com/a1c7e0/switchcraft/releases/tag/test-suite-2026-11-13-r5).
Download `switchcraft-test-suite-2026-11-13-r5.zip` for SD installation. It is
54,717,758 bytes, SHA-256
`008b93e3af2cbb26ed3069f4d5ad336f2721f30256a972ad517a8aa96c0a5a98`.
Source, debug symbols, native SDK and validation logs are separate release
assets; do not copy them onto the SD card.

## Immutable inputs and fixes

- Switchcraft executable/source checkpoint:
  `1d716dbe17f9870e5c2cfbeb351d839ea91412fb`.
- java-switch runtime/SDK/image:
  `a0f0e168bb282e9585c0353c3d9b70a7ad043ce8`.
- Public release-input commit:
  `3f3053607b0685fdb32c9cfe3490920adf2c65f4`.
- [Successful assembly and publication run](https://github.com/a1c7e0/switchcraft/actions/runs/43398648407).

The runtime maps a local `file:/sdmc:/...` URL back to native `sdmc:/...` when
running as Horizon. Maintained JDK JAR/directory loaders and resource streams
share the conversion, including escaped paths. Ordinary Unix paths and file
query handling are preserved; remote authorities do not map to local SD files.
Standalone direct diagnostic builds now refresh their embedded source stamp.
Switchcraft clears, redraws and flushes the complete A/X/Y/B/R/L/+ menu before
input, with its source identity and fresh-process guidance.

SDK ABI 1, genuine JDK and Switchcraft static-provider composition, one VM per
application process, stack/memory policies and safe process termination remain
in force. The complete ten-module instrumented Minecraft profile is included.

## Measured validation and limits

All 92 Switchcraft tests and 23 runtime tests passed. Host checks include real
JDK class/resource loader positive and missing-class negative controls, a
separate sole-localhost-URL loader, JNI/FFM and callbacks, startup-agent
transformation, native provider families, and 60 Java SDL/Vulkan/VMA frames on
Mesa with Khronos validation enabled. The official owned-client renderer
transformation check was enabled. The earlier official snapshot Demo title
capture remains host-only evidence; it was not repeated for this Horizon path
fix. Loopback audio does not establish physical audio output.

The genuine instrumented Minecraft-profile VM, native archives/providers,
classfile-69 image and AArch64 NRO cross-built. Clean source reconstruction and
runtime package verification passed. All nine final NROs have matching ELFs,
source identities and hashes. The combined link has zero undefined symbols and
no GL/EGL API definitions. SD/source/debug/native-SDK inventories and hashes
passed local checks and the GitHub publication workflow; all seven published
asset sizes and server SHA-256 digests match the verified inputs.

R4 physical feedback established zero-services startup and its L private-memory
contract, plus genuine VM creation and java.base loader/error paths. Application
and agent class lookup failed, so Hello, JNI/FFM application, graphics, audio,
shader and Minecraft workloads did not pass. See
[the full R4 report](DEVICE_FEEDBACK_2026_11_13.md).
**R5 Horizon execution and menu readability remain NOT TESTED. Minecraft has
not reached its title screen on Switch.**

## Next physical test

Merge the ZIP into the SD root while preserving saves/configuration. Use
application-mode hbmenu. Begin with one fresh `java25-test` A. Require actual
`Hello from Horizon Java 25` output, Java major 25, status 0 and stage
`completed`. If it fails, stop dependent Java workloads and export that attempt's
native, stdout and stderr logs. If it succeeds, follow
[the ordered checklist](DEVICE_TEST_QUICKSTART.md), restarting the application
for every Java choice. The zero-services L probe is optional for this round.

[The release evidence](evidence/device-r5-package/) preserves final manifests,
input hashes, publication metadata, binary audit and complete validation logs.
The executable/source checkpoint above remains the release identity even when
later documentation commits advance main. Published R4 remains unchanged.
