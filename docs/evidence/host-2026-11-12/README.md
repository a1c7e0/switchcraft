# Linux host title attempt — 2026-11-12

This is a Linux host-only run of the official Minecraft `26.4-snapshot-6`
Demo. It is not evidence of Horizon execution. It reached the Demo title screen
with the official Vulkan path and the existing hash-checked Java agent. No Demo
world was entered.

## Inputs and provenance

- Official version metadata SHA-1: `04be0f389fdac9f1c8b9b551c1e717104a08899d`;
  local metadata SHA-256: `d6f3110b4bbf368cdcd6c02fded7eb80b0a84b4930d5b3f3538562b4295a2c95`.
- Official client SHA-1: `8a97d5dafe80783525a2807b220527b65df724a5`;
  size: 42,156,998 bytes; SHA-256:
  `09d7e86508eb8b01c8e6ecc268ac1e4f8b9f0153c8fcff3201bf3f170199ca8b`.
- Official asset index ID `36`, SHA-1
  `6085c72e1c257db765043c1f31e56487a0eb1e51`, SHA-256
  `cd3836d07a732c0f6bc8e7bf498e10c379346784d881d7c0ba9e4b746f4e6d5c`;
  5,381 unique declared objects, all downloaded and SHA-1 checked by
  `tools/snapshot6-reference.py` into `/tmp/r4-mc-reference`.
- Manifest classpath: the official client plus 67 Linux x86_64 libraries;
  classpath file SHA-256:
  `471dfbf72592618171f93cef5d74e3dc1d1ac750107976cd5d24375f49c7a6c4`.
- Reference helper SHA-256:
  `a22530e6ffd107c8ec96683cc71f0c2ef336ca4d1dcac42432002a2af8787499`.
- Executed VM: Eclipse Temurin OpenJDK `25.0.5+8` Linux x86_64. Its pinned
  archive SHA-256 is
  `68982529869257d0ee6b824ec5aa270ff8b118bb438670da0b97ebdab178d7fb`;
  executable SHA-256 is
  `1bf1aaef01e4f8d7c85d913c60fb2ee4624cbe54d4053254c59657b7ea913b25`.
  This was the desktop Temurin VM, not the Switch Java runtime.
- Strict Vulkan agent JAR SHA-256:
  `2a2ff3124d669649c35a9d6e0353f0e2444ccd6d41f1d9506a0df30e5afd30d4`.
  The log confirms `VULKAN_ONLY_APPLIED` for the snapshot renderer class hash
  `b42d53d78fba06b0fbdb90395dfdc065f319dce9dc037fa4184f9399078ed7ee`.
- The project lock at the time pointed to java-switch revision
  `2d53737168e4aa55601600db3f9d4bc89f9617e4`; that Horizon runtime was not
  executed by this host test.
- Repository HEAD at launch/evidence capture:
  `37b3c061587313cc5c4c68f9afa8aa071abb588e`.
  Other agents had concurrent working-tree changes; this run changed no
  game, Java, native, launcher, dependency lock, or build source. Only the
  evidence files in this directory were created for this task.

The renderer provider was extracted, without installation, from official
Debian Trixie `mesa-vulkan-drivers` version `25.0.7-2+deb13u1`, amd64. Its
SHA-256 is `caf2f7d296b7522efe74e40a74bce762a3ce84c33b53b5e54e1248ac2e0a13a5`,
matching the Debian Trixie `Packages.xz` entry. It lived under
`/tmp/r4-mc-reference/debian-mesa`; no system package was installed. The
application log identifies `llvmpipe Mesa 25.0.7-2+deb13u1 (LLVM 19.1.7)`;
package-index and extraction details are in
[`debian-mesa-provider.txt`](debian-mesa-provider.txt).

## Attempts

### SwiftShader capability failure

The first Vulkan attempt used the installed Chromium SwiftShader ICD. The game
started under the strict agent, then rejected the Vulkan device before backend
creation because it lacked `VK_EXT_vertex_attribute_divisor`,
`vertexAttributeInstanceRateDivisor`, and Vulkan 1.1 `shaderDrawParameters`.
The first-run error screen is [`swiftshader-attempt-01.png`](swiftshader-attempt-01.png). The helper reuses a fixed cache log filename, so the Mesa retry replaced the original failure log. [`swiftshader-attempt-01.log`](swiftshader-attempt-01.log) is a later bounded reproduction of the same failure with the same ICD and pinned inputs; the screenshot is from the original first attempt.

### Mesa llvmpipe Demo title

The fresh Mesa attempt used:

```sh
DISPLAY=:93 SDL_VIDEODRIVER=x11 XDG_RUNTIME_DIR=/tmp \
VK_ICD_FILENAMES=/tmp/r4-mc-reference/debian-mesa/root/usr/share/vulkan/icd.d/lvp_icd.json \
LD_LIBRARY_PATH=/tmp/r4-mc-reference/debian-mesa/root/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH \
timeout --signal=INT --kill-after=10s 150s \
  python3 tools/snapshot6-reference.py \
  --cache /tmp/r4-mc-reference --run-demo \
  --java /workspace/switchcraft/.deps/host-jdk25/jdk-25.0.5+8/bin/java
```

The official snapshot helper verified metadata, client, Linux library artifacts,
and asset objects before launch. Its fixed Linux classpath was used unchanged;
arguments included the official `--demo`, `--graphicsBackend VULKAN`, snapshot
ID, cache game directory/assets/index, and empty access token. No credentials or
game patches were supplied. The existing agent transformed only the exact
hash-pinned renderer preference method.

The renderer initialized, selected llvmpipe, loaded SDL with X11, and completed
resource/texture loading. After selecting the first-run accessibility screen's
Continue button, the screenshot showed the `Minecraft 26.4 Snapshot 6 Demo`
title with `Play Demo World` visible. The app remained open at title until the
150-second outer timeout, which terminated it; no world was entered. The log
also records the expected host-only limitations: no ALSA device (sound disabled)
and unavailable Minecraft Services/Realms network endpoints. Neither stopped
title rendering.

See [`llvmpipe-attempt-02.png`](llvmpipe-attempt-02.png) and
[`llvmpipe-attempt-02.log`](llvmpipe-attempt-02.log). SHA-256 digests for all
six evidence files (this README, provider metadata, both screenshots, and both logs) are listed in [`SHA256SUMS`](SHA256SUMS).
