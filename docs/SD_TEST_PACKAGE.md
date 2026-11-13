# Switchcraft SD device test package

Download **switchcraft-test-suite-2026-11-12-r4.zip** from
[the R4 device test-suite release](https://github.com/a1c7e0/switchcraft/releases/tag/test-suite-2026-11-12-r4).
The SD package is slim: `switch/`, short installation instructions and
manifests/hashes. The matching full source archive is a separate release asset;
it is not in the SD ZIP. Debug symbols are also separate. The manifest records
exact source revisions and the java-switch
runtime revision used for this package. Read that manifest for the pin; do not
infer it from historical package documentation.

## Copy to the SD root

1. Extract the verified ZIP directly into the SD card root, merging its contents.
   The result must include `SD:/switch/java25-test/java25-test.nro` and
   `SD:/switch/minecraft-launcher/minecraft-launcher.nro`; do not copy a wrapper
   folder around these directories.
2. Keep the complete runtime images and diagnostic JARs. NRO files alone are
   insufficient. The package does not supply personal
   launcher configuration, logs, Prism instances, worlds, game assets or accounts.
   Preserve existing user files when merging.
3. Use Switch 1 with Atmosphere and **application-mode hbmenu** (your normal
   title-override setup). Album/applet mode is unsuitable for the Java VM tests.
   No custom game JAR, installation or account is needed for the diagnostics.

The package contains nine applications: switch-diagnostics, java-test, ffi-test,
zero-services-test, vulkan-test, vulkan-present, java25-test, switchcraft-java25
and the graphical minecraft-launcher. It includes miniJVM's Java 8 diagnostic
runtime, the full pinned Java 25 Minecraft module profile with java.instrument, test workloads,
the startup agent, composed SDL native smoke test, and the pinned LWJGL 3.4.3
core JAR at `switch/mc-runtime/libraries/lwjgl-3.4.3.jar`. The combined app's
Y test exercises the packaged LWJGL core JNI subset with SDL/Vulkan FFM calls.
The graphical launcher includes online installation/repair and instance
management.

## Run the tests

For the R4 device run, start with one fresh `java25-test` A attempt. If it prints
Hello, continue in fresh processes with standalone X, standalone Y, combined A,
combined X and combined Y. If a prerequisite fails, stop dependent VM tests and
preserve its logs. The R3 `zero-services-test` launch was reported unable to
start, but no log or crash capture was supplied; its cause is unknown. Its L
probe is optional and must not block Java A. See
[DEVICE_TEST_QUICKSTART.md](DEVICE_TEST_QUICKSTART.md) for details.

For the full checklist:

1. Optional native checks: SD/memory/threads, Java 8 diagnostics and FFI calls.
   `zero-services-test` L and its other actions are not prerequisites; R3 launch
   could not be classified because no log was supplied. A public physical-memory
   mapping action may report unsupported with Result `0xfa01`; record it as
   unsupported, never as a PASS.
2. Genuine Java 25: standalone A (Hello), X (JNI/FFM), Y (startup agent), then
   combined A (Hello), X (SDL JNI/FFM), and Y (LWJGL core JNI plus SDL/Vulkan
   FFM). **Start a fresh application process for every Java 25 action.** Do not
   run multiple VM attempts in one process.
3. After standalone and combined A/X/Y pass, run combined B (60-frame SDL/Vulkan
   presentation and VMA), R (FreeType and OpenAL loopback; no physical audio
   output), and L (STB PNG decode, shaderc compile and SPIR-V Cross reflection),
   each in a fresh process.
4. Vulkan features, presentation/input and offscreen tests. Run deliberate
   SafeFetch fault recovery last, after exporting ordinary logs.
5. Follow [LAUNCHER_TESTS.md](LAUNCHER_TESTS.md) for controller, touch,
   installation/repair, cancellation, profiles, import and archive/restore.

Full case IDs, expected markers and recovery instructions are in
[TEST_PLAN.md](TEST_PLAN.md). A graphics or native test does not establish
Minecraft launch. The Linux host title is separate evidence. R2 evidence
establishes Java 8 diagnostics, the private-memory probe and 300 Vulkan
presentation frames. R3 physical feedback established that `JNI_CreateJavaVM`
returned and `vm-ready` was reached for two selections; `java.base` then ran
missing-class error paths. Hello and Java25Smoke did not execute because their
classes were not found. The startup agent stopped on a missing agent class, and
no JNI, FFM, combined VM, or game test passed. `zero-services-test` could not be
launched and has no log, so no cause is assigned. See
[the preserved feedback](DEVICE_FEEDBACK_2026_11_12.md). R4 changes remain
device-unverified until fresh logs are reviewed.

The required separate `switchcraft-source-2026-11-12-r4.tar.gz` companion includes the
pinned LWJGL, OpenAL Soft, shader-library, libffi, OpenJDK and curl source
archives, repository source and license texts. In particular it includes the
full LWJGL upstream archive at `third-party/upstream/lwjgl3-upstream.tar.gz`;
source archive hashes are recorded in the package manifest and checked against
their dependency pins. Matching debug symbols and the experimental native SDK
are separate artifacts, never part of the SD ZIP.

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
python3 /path/to/SD/switch/mc-runtime/tools/collect-feedback.py --sd-root /path/to/SD --output ./switchcraft-feedback-attempt-01.zip
```

The helper reads an explicit allowlist and does not modify the SD. It includes
the combined manifest, primary logs, tick-named Java stdout/stderr logs,
history/results JSON, latest launcher task report and Java `hs_err_pid*.log`
reports from the standalone and combined app folders. Atmosphere/system crash
dumps are excluded. It excludes accounts, game files and `launch-plan.json`.
Copy any previous JSON report needed before another attempt; review a launch
plan separately before sharing it. Include
firmware/Atmosphere/hbmenu versions, application mode, button/action, wait time
and PASS/FAIL/NOT TESTED for each case.

## Provenance and reproduction

The manifest carries the per-binary Switchcraft source revision, launcher
revision and java-switch revision used by R4. Do not infer the runtime revision
from historical package documentation. R2 device logs recorded Java 8
diagnostic PASS, private L memory-probe PASS including protection, canaries and
cleanup, and 300 Vulkan frames in 5.23 seconds (16.525 ms average turnaround).
Java 25 A reached heap reservation and terminated at `memoryReserver.cpp:521`
because the protection page could not be protected. Java 25 execution and its
dependent JNI/FFM/agent/combined tests remain unachieved.

The installed-file manifest records payload hashes. From an SD-root copy, check
the `switch/` payload with the included SD_FILES_SHA256SUMS:

```sh
sha256sum -c switch/mc-runtime/SD_FILES_SHA256SUMS
```

The build recipe creates the minimal SD ZIP directly from the fresh verified
SD staging tree. It creates the source companion, debug symbols and native SDK
as separate artifacts; it does not create a full build-payload ZIP or copy the
source archive into the SD tree. `scripts/verify-artifacts.sh` checks the
minimal ZIP contents and hashes, the source component pins and license trees,
matching debug ELFs, and required native SDK archives before publication.
