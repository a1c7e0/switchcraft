# Launcher management and installation tests

The launcher now implements online Prism metadata refresh, verified vanilla
resource installation/repair, cancellable background work, local integrity
checks, Prism folder import, settings-only duplication, and archive/restore.
These paths are host-tested and cross-built. **Every Horizon UI/networking and
runtime execution case remains NOT TESTED.** Minecraft launch on Switch is still
blocked by runtime/native integration, independently of resource installation.

Use the [complete R2 SD test package](https://github.com/a1c7e0/switchcraft/releases/tag/test-suite-2026-11-08-r2).
Download the single ready-made ZIP and verify the full ZIP hash before
extracting. It combines the launcher, all standalone Java/native diagnostics and
complete runtime image. Preserve profiles, saves, configuration and logs. No
separate launcher overlay is needed. Use
application-mode hbmenu; see [SD_TEST_PACKAGE.md](SD_TEST_PACKAGE.md).

## First-use path

1. Connect the console using its normal system network settings. Open the launcher.
2. Use L/R to open Versions. Press Y to refresh Prism's catalog. The refresh also
   verifies the fixed snapshot-6 component metadata and suggested LWJGL dependency.
3. Select **26.4-snapshot-6**, press A, then choose **Install / repair files**.
   The task page reports actual file/byte progress. The tested target contains
   5,459 unique artifacts totaling 599,338,934 bytes; allow additional SD space
   for temporary files and metadata. Future catalog data may differ, so retain
   the exact metadata hashes and report instead of assuming those counts.
4. Wait for Complete. Installed status is written only after cryptographic
   verification, not when a version JSON or empty directory appears. Existing
   verified files are reused; the repair action replaces only corrupt managed
   resources after a verified replacement is ready.
5. Return to Versions and select Create an instance, or press X. Set name,
   version and memory, then confirm Create. An uncached selection installs its
   resources before creating the profile; cancellation does not leave a profile
   claiming installation succeeded.
6. Return to Instances, open the card and Check installation. Its plan must use
   the instance's isolated game directory and shared libraries/assets. Runtime,
   authentication and native-binding blockers remain visible. No game is invoked. The snapshot-6 runtime profile is the verified target; other
   catalog entries do not imply game/runtime compatibility.

## Test matrix

| Case | Action | Expected result |
| --- | --- | --- |
| UI-01 | L/R, D-pad/stick, touch and system keyboard | Focus and activation agree; text is readable; B returns without saving drafts |
| UI-02 | Change light/dark and memory, save, reopen | Preferences persist; unrelated config fields survive |
| NET-01 | Versions Y on normal network | Catalog and indexed SHA-256-verified component JSON appear; no installed receipt yet |
| NET-02 | Install snapshot-6 | Client/libraries/assets verify; task completes and installed receipt records the pinned version |
| NET-03 | Cancel an active download with B | Worker cancels and joins; verified files remain reusable; no false Complete/profile |
| NET-04 | Retry cancelled installation | Valid files are reused and remaining files are checked/downloaded |
| NET-05 | Verify local files | Actual hashes/sizes are checked; missing/corrupt files are reported; verification does not alter game data |
| NET-06 | Disconnect network during install, then reconnect and retry | Visible error/retry; no successful receipt for an incomplete installation |
| INST-01 | Create, reopen, rename and edit memory | Prism cfg/pack persist; shared installation and other profiles are unchanged |
| INST-02 | Change version | Cached component dependencies are recomputed; unsupported component changes fail before overwriting the profile |
| INST-03 | Duplicate settings | Component pack, scalar settings and local patches copy; duplicate game directory is empty |
| INST-04 | Archive, first cancel; then confirm | Cancel leaves the profile untouched; confirm moves it and all saves into the archive |
| INST-05 | Settings > Archived instances > Restore | Files return unchanged; a colliding active ID is preserved and a new ID is selected |
| INST-06 | Import a Prism profile folder | Source stays unchanged; profile, patches and game files copy to a new managed instance |
| INST-07 | Cancel import | Partial destination is removed; source and existing instances remain unchanged |
| LIFE-01 | Press + while a worker is active | Cancellation is requested; process does not unload worker code before join |
| DIAG-01 | Open each available diagnostic from Diagnostics | Existing NRO launches; Java25 tests still require new application processes |

Do not deliberately corrupt an owned world to test repair. For corruption tests,
use a disposable cache or an expendable downloaded library, preserve a backup,
and record its exact hash/path. An unowned `.part` file is preserved/refused.
Only a matching `.part.owner` journal permits explicit repair to restart an
interrupted managed download. Completed files are cached; partial bytes are
clean-restarted rather than claimed as range-resumed.

The transfer/import worker uses a 512 KiB native stack. This manager is VM-free;
it does not alter the Java diagnostic stack/heap policies or the one-VM-per-process
rule. Long network calls remain subject to the transport's configured timeouts.

Folder import accepts `.minecraft/` or Prism's `minecraft/` directory and rejects
symlinks/special files. Defaults are 20,000 files and 2 GiB, with bounded depth.
Imported desktop memory settings are clamped to the supported 128..1024 MiB
range in the destination; the source is not rewritten. This is a launcher
policy, not a measured Minecraft heap recommendation.

## Logs and recovery

`switch/mc-runtime/logs/minecraft-launcher.log` appends task starts, outcomes and
errors. `launcher-task-report.json` contains the most recent structured task
result; `launch-plan.json` contains the most recent explicit plan export. These
JSON reports are overwritten, so save a per-attempt copy before repeating.
The R2 collect-feedback helper includes the task report and unique tick-named
Java VM stdout/stderr logs, while excluding account data, game assets,
launch-plan.json and crash reports.

If a network or import worker stalls, record the action, actual wait, last
message and HOME responsiveness. Use HOME/close if necessary. Device timing,
TLS service behavior, touch and keyboard execution have no physical acceptance
result yet. TLS verification is enabled; do not disable it to force a pass.
An optional `network_ca_file` in launcher.json supplies an explicitly chosen CA
bundle. The normal default uses the configured system trust store.

## Host reproduction

The 2026-11-04 acceptance run passed all **55 launcher tests** above and **11
additional artifact, resolver, host JNI/FFM, LWJGL identity and renderer tests**.
Logs are retained under docs/evidence as launcher-final-55-tests-HOST-ONLY.log
and launcher-integration-11-tests-HOST-ONLY.log. The real online installation
report is launcher-online-install-HOST-ONLY.json; this is not a fixture download.

The expanded host run initially used a stale shared Java checkout. The two affected
resolver/JNI tests then passed using an isolated runtime pin. These are host
results for that older integration, not the new R2 runtime revision.
One additional archive-mutation test could not be rerun: the original pinned
SDK/runtime `.tar.gz` inputs are absent from this restored workspace. The
previously integrated SDK/image remain cached and unchanged; no new VM/image
build is claimed. The initial complete errors are retained in
launcher-expanded-initial-environment-errors.log. Recreate those original
artifacts through the full pinned runtime build before rerunning
tests.test_java25_package. This is a host cache prerequisite, not a measured
Horizon runtime defect.

Install a C++17 compiler, Python 3, pkg-config, libcurl development files and
OpenSSL development files/CLI. From the repository root:

```sh
make build/switchcraft-install build/switchcraft-inspect build/launcher-preview
python3 -m unittest tests.test_metadata tests.test_config tests.test_instances tests.test_prism_metadata tests.test_prism_cache tests.test_ui_canvas tests.test_launcher_controller tests.test_launcher_session tests.test_launcher_jobs tests.test_download tests.test_install tests.test_feedback -v
build/switchcraft-install /tmp/switchcraft-cache install 26.4-snapshot-6
build/switchcraft-install /tmp/switchcraft-cache verify 26.4-snapshot-6
```

Use a private cache outside Git/dist. The installer targets Horizon library rules;
Linux title-reference native libraries are a separate workload. No game payloads
from a host run are included in source or release artifacts. Microsoft login,
modloader installation and the complete Qt task framework are not implemented.

The real client was also launched on 2026-11-04 and visually reached its Demo
title using the strict Vulkan bridge, then exited normally. Follow
[HOST_REFERENCE.md](HOST_REFERENCE.md) for that independent host test and retained
evidence. A resource-install PASS alone does not establish game startup.
