# Existing-task baseline: f93bfc0

* Switchcraft `f93bfc005cddb77a1f4ddc44d1b14d67d6a2797d`, branch `main`.
* java-switch pin `9f6ac4efc04a1750fe54c62d72c4401fda89e68a`, ABI 1.
* `bash scripts/build-all.sh`: PASS in the existing pinned toolchain/cache.
  Main host suite 12 tests PASS; Java dependency host suite 5 tests PASS.
* Six AArch64 NRO0/ASET/NACP/icon/build-ID checks and package SHA/ZIP checks:
  PASS. These are build and host checks, not Horizon execution.
* Existing install ZIP SHA-256:
  `89d0b2ea56ad0253885c20c9bfcf50d0e0dcdbb65031e37ac24327ed6d87c5c3`.
  Preserved at `/tmp/switchcraft-baseline-f93bfc0.zip` in this environment and
  on the `artifacts/vmem-f93bfc0` delivery branch. New builds may produce
  different archive hashes because build timestamps are recorded.
* Official snapshot Demo title with Vulkan: HOST ONLY, previously visually
  reviewed; see HOST_REFERENCE.md and its evidence. Java 25 Horizon VM and
  Minecraft title on Horizon: BLOCKED / NOT ACHIEVED.
* All physical Switch CPU/GPU/input/runtime tests: NOT TESTED. No device is
  attached to this environment. `legacy/1.12.2` remains at feb2f4d.
