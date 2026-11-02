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
