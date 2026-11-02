# Switchcraft

Native Horizon homebrew diagnostics, a Java interpreter test, and a Minecraft
installation inspector for Nintendo Switch 1. **Minecraft is not playable in
this release. Every NRO is cross-compiled; Switch hardware execution is NOT TESTED.**

## Delivered applications

| NRO | Implemented behavior |
| --- | --- |
| `switch-diagnostics.nro` | Controller menu, process memory query, bounded allocation, exclusive SD read/write, native threading, navigation to other NROs |
| `opengl-test.nro` | Mesa NVC0/EGL context, API strings/extensions, visible green triangle, pixel readback and clean teardown |
| `vulkan-test.nro` | Experimental Mesa NVK device/features/queues/heaps report, GPU buffer fill/readback, offscreen triangle with pixel verification |
| `java-test.nro` | miniJVM interpreter, bundled Java 8 JAR suite, separate-JAR loading, reflection, threads, file I/O, allocation, exceptions, static native bridge; optional `user.jar` |
| `minecraft-launcher.nro` | Installed version selection, inherited JSON resolution, rule evaluation, classpath/argument plan, missing-file/native checks, settings and diagnostics navigation |

The launcher exports a blocked launch plan. It does not execute Minecraft.
The miniJVM bridge is not the standard JNI Invocation API. OpenJDK, Vulkan
presentation, LWJGL, audio, Microsoft authentication and Fabric are unfinished.

## Build

Linux x86_64, Python 3.12+, GCC/G++, GNU Make 4.3+, `patch`, Git and HTTPS
access are required. No root installation is necessary:

```sh
bash scripts/build-all.sh
```

This fetches a digest-pinned devkitPro toolchain and hash-locked dependencies,
builds five NROs, runs host tests, verifies NRO/ASET/NACP and AArch64 ELF metadata,
then creates `dist/switch-minecraft-test-package.zip`, `dist/COPY_TO_SD/`,
`dist/manifest.json` and `dist/SHA256SUMS`. Debug ELFs remain in `build/`.
The first build needs several GB of disk; subsequent builds reuse downloads.
See [BUILD.md](docs/BUILD.md) for Docker, proxy CA handling and exact versions.

## Install and first tests

1. Extract `dist/switch-minecraft-test-package.zip` to the SD root. Merge
   directories and preserve existing saves/configuration. No game files or real
   `launcher.json` are included in the package.
2. Use **application-mode Homebrew Menu** on Atmosphère, commonly by holding R
   while starting an installed title. Start `switch-diagnostics`. Applet-mode
   memory measurements do not represent full application memory.
3. Run memory, SD and threading tests first; then test OpenGL and Vulkan
   separately. Follow [TEST_PLAN.md](docs/TEST_PLAN.md) before the Java test.

No Linux, Android, kernel patches, overclocking, proprietary SDK or external
game-execution server is required by these NROs.

## Import and configuration

Copy your legitimately obtained installation's `versions/`, `libraries/` and
`assets/` into `sdmc:/minecraft/.minecraft/`. Other normal directories may remain
there. The inspector reads this root and never alters its game files or saves.
It plans an isolated game directory under
`sdmc:/switch/mc-runtime/instances/test/<version>/`.

For a different root, copy
`sdmc:/switch/mc-runtime/config/launcher.example.json` to `launcher.json` and
edit `minecraft_root`. In the inspector: D-pad selects a version, L selects a
runtime target, R selects graphics, A inspects/exports, X saves settings, Y opens
diagnostics, minus displays recent logs, plus exits. Runtime and graphics choices
describe plans and diagnostic backends, not available Minecraft support.

The default planned heap is 256 MiB. The separate Java diagnostic uses a 64 MiB
GC target; native allocations are not covered by a hard process quota.

To try your own small Java 8 program, compile a class named `UserMain`, package
it in `sdmc:/switch/mc-runtime/tests/user.jar`, and press X in `java-test`.
It receives an isolated diagnostic directory as its first argument. Use your
own trusted test code. Dynamic native loading and process creation are disabled.

## Logs and evidence

Copy the entire `sdmc:/switch/mc-runtime/logs/` directory back after testing.
It contains per-application plain-text logs and `launch-plan.json`. Logs contain
no supplied account credentials; authentication placeholders remain unresolved.
`dist/manifest.json` records source revision, dependency/toolchain versions,
checksums, build verification and hardware status.

Host tests pass for the interpreter suite and metadata behavior. An additional
host Minecraft 1.12.2 bootstrap experiment reached its main class and failed in
LWJGL initialization; no title screen or game rendering was reached. See
[IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md).

## Engineering documents

* [Architecture and diagrams](docs/ARCHITECTURE.md)
* [Upstream source research and licensing](docs/UPSTREAM_RESEARCH.md)
* [Build instructions](docs/BUILD.md)
* [Hardware test plan](docs/TEST_PLAN.md)
* [Compatibility](docs/COMPATIBILITY.md)
* [Known issues](docs/KNOWN_ISSUES.md)
* [Implementation evidence](docs/IMPLEMENTATION_STATUS.md)
* [Decisions](docs/DECISIONS.md)
* [Next steps](docs/NEXT_STEPS.md)

Original project code is MIT. Third-party licenses are retained in `licenses/`.
The miniJVM Java class library is GPL-2.0 with additional notices in individual
files; its full source accompanies the install package. A binary-only
distribution does not remove those obligations. No Minecraft game code,
OptiFine, assets, Microsoft tokens or console keys are distributed.
