# Complete Switchcraft SD test package

Download **switchcraft-complete-test-suite-2026-11-08-r2.zip** from
[the R2 complete test-suite prerelease](https://github.com/a1c7e0/switchcraft/releases/tag/test-suite-2026-11-08-r2).
Download the single ZIP and optionally SHA256SUMS. No split-file assembly or
separate runtime/launcher overlay is needed. The publishing workflow internally
reassembles transport parts; the user-facing release contains the finished ZIP.
The manifest records exact source revisions and the new runtime pin.

## Copy to the SD root

1. Extract the verified ZIP directly into the SD card root, merging its contents.
   The result must include `SD:/switch/java25-test/java25-test.nro` and
   `SD:/switch/minecraft-launcher/minecraft-launcher.nro`; do not copy a wrapper
   folder around these directories.
2. Keep the complete runtime images, diagnostic JARs, source archives and notices.
   NRO files alone are insufficient. The package does not supply personal
   launcher configuration, logs, Prism instances, worlds, game assets or accounts.
   Preserve existing user files when merging.
3. Use Switch 1 with Atmosphere and **application-mode hbmenu** (your normal
   title-override setup). Album/applet mode is unsuitable for the Java VM tests.
   No custom game JAR, installation or account is needed for the diagnostics.

The package contains nine applications: switch-diagnostics, java-test, ffi-test,
zero-services-test, vulkan-test, vulkan-present, java25-test, switchcraft-java25
and the graphical minecraft-launcher. It includes miniJVM's Java 8 diagnostic
runtime, the genuine Java 25 java.base/java.instrument image, test workloads,
the startup agent, composed SDL native smoke test, source and notices. The
launcher includes online installation/repair and instance management.

## Run the tests

Start with [DEVICE_TEST_QUICKSTART.md](DEVICE_TEST_QUICKSTART.md):

1. Native prerequisites: SD/memory/threads, Java 8 diagnostic and FFI calls.
   Run the private memory-mapping probe first. A public physical-memory mapping
   action may report unsupported with Result `0xfa01`; record it as unsupported,
   never as a PASS. The private probe is the relevant first memory test.
2. Genuine Java 25: standalone A (Hello), X (JNI/FFM), Y (startup agent), then
   combined A (Hello) and X (SDL JNI/FFM). **Start a fresh application process
   for every Java 25 action.** Do not run multiple VM attempts in one process.
3. Vulkan features, presentation/input and offscreen tests. Run deliberate
   SafeFetch fault recovery last, after exporting ordinary logs.
4. Follow [LAUNCHER_TESTS.md](LAUNCHER_TESTS.md) for controller, touch,
   installation/repair, cancellation, profiles, import and archive/restore.

Full case IDs, expected markers and recovery instructions are in
[TEST_PLAN.md](TEST_PLAN.md). A graphics or native test does not establish
Minecraft launch. The Linux host title is separate evidence. Horizon VM startup,
Java, JNI/FFM, instrumentation, graphics and Minecraft execution remain NOT
TESTED with the R2 package until fresh Switch logs establish results.

## Export logs

Most text logs append, so export after distinct ordinary tests and before
repeating a case or trying a deliberate fault. Profile, launcher-task and
launch-plan JSON files hold only the most recent result. The Java VM stdout and
stderr files have unique tick-based names; preserve all files for each attempt
with the corresponding app log. A fatal VM abort can end the process before the
result screen can be held; retain the log's relative PC/register capture and any
system crash report.

On a PC with Python 3, run the included helper, substituting the mounted SD path
and a new output filename outside the SD card:

```sh
python3 /path/to/SD/switchcraft-docs/collect-feedback.py --sd-root /path/to/SD --output ./switchcraft-feedback-attempt-01.zip
```

The helper reads an explicit allowlist and does not modify the SD. It includes
the combined manifest, primary logs, tick-named Java stdout/stderr logs,
history/results JSON and latest launcher task report. It excludes accounts,
game files and launch-plan.json. Copy any previous JSON report needed before
another attempt; review a launch plan separately before sharing it. Include
firmware/Atmosphere/hbmenu versions, application mode, button/action, wait time
and PASS/FAIL/NOT TESTED for each case.

## Provenance and reproduction

R2 is freshly built from the fullpackager inputs. Its manifest carries the
per-binary Switchcraft source revision, launcher revision and java-switch
revision used for the new genuine runtime. Do not infer the runtime revision
from the historical B7 package. The package includes sources and licenses.
R2 host build/test results do not establish new physical results. Historical B7
Switch logs include native/FFI/SafeFetch/Vulkan successes, Java 8 filesystem
failures, memory commit Result `0xfa01`, and Java 25 data aborts before VM output.
The Java 8 fix, fallback memory behavior and new VM failure diagnostics need
fresh R2 device evidence.

The installed-file root manifest records payload hashes. From an SD-root copy,
check its files with the included SD_FILES_SHA256SUMS:

```sh
sha256sum -c switchcraft-docs/SD_FILES_SHA256SUMS
```

The **Publish device test package** workflow reads `RELEASE_INPUTS.json` from a
full immutable public commit, verifies the ordered public ZIP parts, whole ZIP,
manifest and SHA256SUMS, validates the nine NROs and runtime/test resources, and
uploads only to the matching draft prerelease. It does not build a runtime or
overlay earlier binaries. No private Java checkout or runtime-build secret is
used.
