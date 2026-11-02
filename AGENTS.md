# Switchcraft engineering guide

All documentation is written in English. Commit meaningful milestones.
Never claim hardware execution from a successful cross-compilation.
Never ship placeholder NROs, game JARs, credentials, or authentication bypasses.

## Layout and commands

* `src/`: Horizon applications and shared platform services.
* `scripts/`: pinned toolchain bootstrap, builds, validation and packaging.
* `tests/`: host tests and original Java diagnostic programs.
* `docs/`: evidence, architecture, upstream decisions and hardware test plan.
* `dist/`: generated artifacts, ignored by Git.

Bootstrap: `python3 scripts/bootstrap-toolchain.py` (Python 3.12+).
The OCI extraction fallback avoids Docker vfs copy amplification on small disks.
The image digest is pinned in the script; do not change it without rebuilding.

Use libnx application mode for memory testing. No Linux/Android on the console,
kernel patches, overclocking, proprietary SDKs, or remote game execution.
Keep platform code separate from metadata processing. Treat native PC libraries
as incompatible until a Horizon implementation is linked and verified.

## Current evidence and constraints

The initial GitHub repository was empty. The managed environment has GCC,
Python and a working Docker daemon but only 7.9 GB disk. Docker vfs exhausted
disk during container creation; the pinned-image extraction is the fallback.
See `docs/IMPLEMENTATION_STATUS.md` for current milestones and next actions.

## Completed baseline and continuation

`bash scripts/build-all.sh` verifies dependencies, builds five NROs, runs host
tests and packages/validates the SD ZIP. `make host-test` exercises real Java
JARs through the patched miniJVM interpreter plus metadata and NRO validation.
Run `python3 scripts/bootstrap-deps.py` after changing the miniJVM patch; it
recreates `.deps/minijvm` before rebuilding. Never edit generated `.deps` as the
only record of a fix: update `patches/minijvm-horizon.patch` or tracked adapters.

`dependencies.lock.json` fixes image/archive revisions and hashes. OpenGL uses
the image's Mesa 20.1.0; NVK is a separate Mesa 25.0.7 static binary release.
Do not link both drivers into one NRO. Vulkan currently renders offscreen only.
miniJVM uses classic GC, disabled JIT, semicolon classpaths, no subprocesses or
dynamic natives. Its static native method ABI is not standard JNI Invocation.
The host Java suite passes; Horizon execution remains NOT TESTED.

The inspector reads `.minecraft` and writes only runtime settings/logs/plans.
It always exports `launchable=false` until a Minecraft-capable backend exists.
Do not add a nonfunctional Play button. Official metadata covers Java 8/17/21/25.
The separate host 1.12.2 bootstrap failed at missing Java APIs/AWT/LWJGL; no game
files are tracked or packaged. AOT is blocked on absent external pz-switch and
GraalVM/game inputs. Preserve these boundaries in documentation and manifest.

Next: collect physical Switch logs using `docs/TEST_PLAN.md`, fix any platform
failure, add Vulkan presentation, reconstruct a self-contained OpenJDK port,
then integrate LWJGL and a legitimate game instance. Keep debug ELFs to resolve
crash offsets. Final release hashes and source revision live in `dist/manifest.json`.
