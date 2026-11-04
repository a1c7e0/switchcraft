# Physical test plan — snapshot 6 mainline

Every physical case begins as **NOT TESTED**. The Linux Demo title is separate
reference evidence; the Horizon game title remains **BLOCKED / NOT ACHIEVED**.
L-01 through L-03 below describe the console inspector in the immutable
`artifacts/java25-e08f36a` base package. The newer
[launcher overlay](https://github.com/a1c7e0/switchcraft/tree/artifacts/launcher-manager)
changes launcher controls to a graphical UI; use [PRISM_PORT.md](PRISM_PORT.md)
for controls and [LAUNCHER_TESTS.md](LAUNCHER_TESTS.md) for installation and
management checks. It does not replace the Java diagnostic NROs.
Use Switch 1, Atmosphere, application-mode hbmenu, normal clocks and supported
libnx APIs. No patches or Linux/Android boot. Keep SD backups and preserve saves
and real configuration when merging the package.

Common installation/launch for each NRO: extract the complete test ZIP to the SD
root and start `sdmc:/switch/<name>/<name>.nro` in application-mode hbmenu, or use
the explicitly named diagnostic next-load action. Logs named below are relative
to `sdmc:/switch/mc-runtime/logs/`. The common prerequisites apply to every case.

For a first session, follow [DEVICE_TEST_QUICKSTART.md](DEVICE_TEST_QUICKSTART.md).
Run N-01 through N-04, J-01, F-01 through F-04 and Z-01 through Z-04 before
the genuine Java25 sessions. Z-05 is an advanced deliberate-fault probe; export
ordinary logs before attempting it. Graphics V-01 through V-04 are an independent
branch. Proceed to optional launcher checks afterward. A feature-profile PASS is not a
Minecraft title PASS. Standard JNI/FFM host tests are not Horizon runtime tests.

## J25-01 — independent Java 25 Hello

* **File:** `java25-test.nro`; install the complete package including the
  OpenJDK image, Java25 JARs, source and notices.
* **Launch/action:** Start via application-mode hbmenu in a fresh process and
  press A once. The 4 MiB worker join pauses UI updates.
* **Pass:** SDK stage `completed` and `Hello from Horizon Java 25` in VM stdout.
* **Failure/report:** Capture status/stage, raw Results, firmware, Atmosphere,
  application mode, package hash, last action, approximate wait and crash report.
* **Logs:** `java25-test.log`, `java25-vm-stdout.log`, `java25-vm-stderr.log`.
* **Risk/recovery:** Moderate; HOME and close the application if stalled. After
  a completed VM session use + and reopen application-mode hbmenu in a new process.

## J25-02 — JNI/FFM and agent, separate fresh processes

* **File:** `java25-test.nro`; J25-01 passed and the complete package is installed.
* **Launch/action:** In a fresh process press X; after exit start another fresh
  process and press Y for the genuine startup-agent/Class-File API test.
  Y requires the packaged instrument-enabled image and both
  `java25-agent-smoke-agent.jar` and `java25-agent-smoke-app.jar` in tests/.
* **Pass:** X prints `JAVA25 JNI FFM SUITE PASS`; Y prints
  `JAVA25_AGENT_SMOKE_PASS`, with stage `completed`. Host markers do not count.
* **Failure/report:** Preserve every line and actual native Result/exception,
  last action, approximate wait, firmware, mode, package hash and crash report.
* **Logs:** All three files named in J25-01.
* **Risk/recovery:** Moderate; HOME/close on stall. Do not reuse a VM process or
  apply privileges/patches to force a pass.

## J25-03 — combined Switchcraft/JDK resolver

* **File:** `switchcraft-java25.nro`; J25-01/02 passed and application-mode
  hbmenu is active. Install the full openjdk25 image and `java25-hello.jar`.
* **Launch/action:** Start in a fresh process and press A once. Resolver preflight
  checks JDK, SDL3 and Vulkan real symbol addresses, then attempts Java25 Hello.
* **Pass:** All preflight statuses 0, VM stage `completed`, and `Hello from
  Horizon Java 25` in the combined VM stdout log. The application exits its
  process; reopen hbmenu before further tests.
* **Failure/report:** All status/Result lines, process memory/heap override,
  artifact hash, firmware, application mode, action, wait and crash report.
* **Logs:** `switchcraft-java25.log`, `switchcraft-java25-vm-stdout.log`,
  `switchcraft-java25-vm-stderr.log` under the common log root.
* **Risk/recovery:** Moderate; HOME/close on a stall. These results do not prove
  LWJGL FFM, Minecraft initialization, rendering or a title screen.

## J25-04 — Java JNI/FFM call to linked SDL3

* **File:** `switchcraft-java25.nro`; J25-01/02/03 passed and the complete
  package including `switchcraft-native-smoke.jar` is installed.
* **Launch/action:** Start in another fresh application-mode process and press X.
* **Pass:** Provider preflight passes, VM stage is `completed` and VM stdout
  contains `SWITCHCRAFT_SDL_FFM_PASS SDL_version=` with SDL major 3. The Java
  workload registers JNI methods, resolves real SDL/Vulkan addresses and calls
  SDL_GetVersion via the JDK FFM fallback. It does not create a window.
* **Failure/report:** Complete three combined VM logs, first Java exception,
  raw Result, package hash, firmware, mode, last action, wait and crash report.
* **Logs:** The three `switchcraft-java25` logs from J25-03.
* **Risk/recovery:** Moderate; HOME/close if stalled; reopen hbmenu for each
  attempt. Do not infer Minecraft, SDL rendering or title compatibility.

## N-01 — switch-diagnostics.nro

* **File:** `switch-diagnostics.nro`.
* **Installation requirements:** Common setup; Application-mode hbmenu, complete package.
* **How to launch:** Common hbmenu launch for the named NRO; the explicitly marked host/future cases are exceptions.
* **Controller operations / actions:** Launch, inspect readable menu, D-pad through eight entries; + exits.
* **Expected screen/output and successful result:** Correct selection/input and clean hbmenu return.
* **Failure symptoms:** Black screen, no input, wrong entry, failed exit.
* **Log location:** `switch-diagnostics.log` under the common log root unless explicitly host/manifest.
* **Information to report:** Firmware, Atmosphere/hbmenu, launch mode, model/controller, source/hash.
* **Risk level:** Low.
* **Recovery steps:** HOME/relaunch; test individual NRO directly if next-load fails.

## N-02 — switch-diagnostics.nro

* **File:** `switch-diagnostics.nro`.
* **Installation requirements:** Common setup; Writable SD; preserve any existing diagnostic.tmp.
* **How to launch:** Common hbmenu launch for the named NRO; the explicitly marked host/future cases are exceptions.
* **Controller operations / actions:** Choose SD filesystem roundtrip, A.
* **Expected screen/output and successful result:** Read/write/compare PASS and remove=0; no .minecraft changes.
* **Failure symptoms:** errno or existing-file refusal; no existing temp file should be overwritten.
* **Log location:** `switch-diagnostics.log` under the common log root unless explicitly host/manifest.
* **Information to report:** Full errno, SD type/free space/filesystem.
* **Risk level:** Low.
* **Recovery steps:** Exit; preserve logs and any preexisting file before removing only a confirmed test leftover.

## N-03 — switch-diagnostics.nro

* **File:** `switch-diagnostics.nro`.
* **Installation requirements:** Common setup; Full application memory, default clocks.
* **How to launch:** Common hbmenu launch for the named NRO; the explicitly marked host/future cases are exceptions.
* **Controller operations / actions:** Choose Memory report, A.
* **Expected screen/output and successful result:** Process total/used, malloc arena/free, 4 MiB allocation/access/free PASS.
* **Failure symptoms:** svcGetInfo or allocation failure, freeze.
* **Log location:** `switch-diagnostics.log` under the common log root unless explicitly host/manifest.
* **Information to report:** Raw process and allocator byte counts; applet type.
* **Risk level:** Low.
* **Recovery steps:** HOME/relaunch; do not assume all physical 4 GB is usable heap.

## N-04 — switch-diagnostics.nro

* **File:** `switch-diagnostics.nro`.
* **Installation requirements:** Common setup; Normal native setup.
* **How to launch:** Common hbmenu launch for the named NRO; the explicitly marked host/future cases are exceptions.
* **Controller operations / actions:** Choose Thread create/join, A.
* **Expected screen/output and successful result:** Result=0 and sum=500500 PASS.
* **Failure symptoms:** Nonzero Result, incorrect sum, hang.
* **Log location:** `switch-diagnostics.log` under the common log root unless explicitly host/manifest.
* **Information to report:** Create/start/join Result and last stage.
* **Risk level:** Low.
* **Recovery steps:** HOME/relaunch and retain matching ELF if it crashes.

## V-01 — vulkan-present.nro

* **File:** `vulkan-present.nro`.
* **Installation requirements:** Common setup; Application mode, packaged NVK; start independently.
* **How to launch:** Common hbmenu launch for the named NRO; the explicitly marked host/future cases are exceptions.
* **Controller operations / actions:** Press A for exact snapshot profile.
* **Expected screen/output and successful result:** GPU/API plus eight feature flags and three required extensions logged; snapshot-vulkan.json written. Mark compatible only if every base requirement passes.
* **Failure symptoms:** No device, API error, missing feature/extension, missing JSON.
* **Log location:** `vulkan-present.log and snapshot-vulkan.json` under the common log root unless explicitly host/manifest.
* **Information to report:** Full JSON/log; missing base features do not imply a porting mistake or justify faking support.
* **Risk level:** Moderate: experimental driver.
* **Recovery steps:** HOME if hung; retain last stage; run platform diagnostics separately.

## V-02 — vulkan-present.nro

* **File:** `vulkan-present.nro`.
* **Installation requirements:** Common setup; Native basics passed; display and controller connected.
* **How to launch:** Common hbmenu launch for the named NRO; the explicitly marked host/future cases are exceptions.
* **Controller operations / actions:** Press X; observe color-changing window; Plus/Start ends test, or wait up to 300 frames.
* **Expected screen/output and successful result:** SDL Switch video, VI surface/swapchain, visible color frames, nonzero presented count; returns to console.
* **Failure symptoms:** SDL/window/surface errors, black output, swapchain/fence errors or freeze.
* **Log location:** `vulkan-present.log` under the common log root unless explicitly host/manifest.
* **Information to report:** Driver/window dimensions/format, frames, visible output and HOME responsiveness.
* **Risk level:** Moderate.
* **Recovery steps:** Use Plus/Start if responsive; HOME/relaunch otherwise; no GPU reset is promised.

## V-03 — vulkan-present.nro

* **File:** `vulkan-present.nro`.
* **Installation requirements:** Common setup; V-02 with Joy-Con or Pro Controller.
* **How to launch:** Common hbmenu launch for the named NRO; the explicitly marked host/future cases are exceptions.
* **Controller operations / actions:** During X presentation press ordinary buttons, then SDL Start. For a standard paired/Pro controller the pinned SDL driver maps Plus to SDL Start and physical A to SDL East (which also exits); single Joy-Con mappings differ. Record the physical button and logged SDL name.
* **Expected screen/output and successful result:** SDL gamepad name, instance ID, numeric button ID and SDL button name appear in the log; exit input works. These are expected static mappings, not a hardware PASS.
* **Failure symptoms:** No gamepad, missing/repeated events, cannot exit.
* **Log location:** `vulkan-present.log` under the common log root unless explicitly host/manifest.
* **Information to report:** Exact controller/mode, event IDs and buttons that failed; this is not yet in-game controller verification.
* **Risk level:** Moderate.
* **Recovery steps:** Wait for 300 frames or HOME; reconnect controller and retest baseline.

## V-04 — vulkan-test.nro

* **File:** `vulkan-test.nro`.
* **Installation requirements:** Common setup; V-01 GPU enumeration usable.
* **How to launch:** Common hbmenu launch for the named NRO; the explicitly marked host/future cases are exceptions.
* **Controller operations / actions:** A enumerates; X runs fill/readback; Y runs offscreen triangle.
* **Expected screen/output and successful result:** 4096 words equal cafebabe; triangle center/corner PASS with ASCII preview. This is distinct from VI presentation.
* **Failure symptoms:** Allocation/submit/fence/pixel mismatch, crash.
* **Log location:** `vulkan-test.log` under the common log root unless explicitly host/manifest.
* **Information to report:** All VkResults, mismatch index/pixels, last stage, profile JSON.
* **Risk level:** Moderate.
* **Recovery steps:** Timeout exits without freeing pending work; HOME if driver itself hangs.

## F-01 — ffi-test.nro

* **File:** `ffi-test.nro`.
* **Installation requirements:** Common setup; Complete package; normal application mode.
* **How to launch:** Common hbmenu launch for the named NRO; the explicitly marked host/future cases are exceptions.
* **Controller operations / actions:** Press A.
* **Expected screen/output and successful result:** Integer AAPCS64 downcall=42 and mixed integer/FP=41.5 PASS.
* **Failure symptoms:** Wrong result, crash or missing entry.
* **Log location:** `ffi-test.log` under the common log root unless explicitly host/manifest.
* **Information to report:** Both results and last stage; attach matching ELF/crash addresses.
* **Risk level:** Moderate: native ABI test.
* **Recovery steps:** HOME/relaunch on failure; do not run custom closures before basic downcalls.

## F-02 — ffi-test.nro

* **File:** `ffi-test.nro`.
* **Installation requirements:** Common setup; F-01 passed; no custom system patches.
* **How to launch:** Common hbmenu launch for the named NRO; the explicitly marked host/future cases are exceptions.
* **Controller operations / actions:** Press X once.
* **Expected screen/output and successful result:** Real jitCreate/RW-RX preparation and upcall=42; jitClose=0. Unsupported permission must be reported honestly.
* **Failure symptoms:** libnx Result, bad ffi_status, wrong value, crash.
* **Log location:** `ffi-test.log` under the common log root unless explicitly host/manifest.
* **Information to report:** Every Result/code, closure phase and whether HOME responded.
* **Risk level:** Moderate: supported executable-memory APIs.
* **Recovery steps:** HOME/relaunch; do not install kernel patches or overclock to force a pass.

## F-03 — ffi-test.nro virtual memory

* **File:** `ffi-test.nro`.
* **Installation requirements:** Common setup; application-mode hbmenu and the latest test package.
* **How to launch:** Start `ffi-test` from application-mode hbmenu.
* **Controller operations / actions:** Press Y once, wait for all results, then + to exit.
* **Expected screen/output and successful result:** 64 KiB reserved, commit/readback PASS, uncommit, recommit and release status=0 and Result=0.
* **Failure symptoms:** Reservation failure, nonzero status/Result, failed readback, hang or crash.
* **Log location:** `sdmc:/switch/mc-runtime/logs/ffi-test.log`.
* **Information to report:** Each status and Result, last stage, package hash and launch mode.
* **Risk level:** Moderate: supported native address-space and mapping syscalls.
* **Recovery steps:** Use HOME/relaunch if necessary; preserve logs and crash report. A denied syscall is a diagnostic result; do not add system patches.

## F-04 — ffi-test.nro partial virtual memory

* **File/action:** `ffi-test.nro`, B, after ordinary downcalls and the Y memory probe.
* **Pass:** 64 KiB-aligned reservation; middle two-page mapping/readback;
  R/NONE/RW protection changes; partial uncommit/recommit and release succeed.
* **Report:** Every status and raw Result from `ffi-test.log`. The probe never
  deliberately accesses NONE or unmapped memory. A denied syscall is not PASS.
* **Recovery:** A failed release is retained; Y/B first retries cleanup before
  another reservation. HOME/close if stalled; keep the last stage and wait time.

## Z-01 through Z-04 — standalone VM service prerequisites

* **File/setup:** `zero-services-test.nro`, complete package, application-mode
  hbmenu. This contains native OpenJDK components, no Java VM.
* **Z-01 / A:** Clocks, semaphore accounting, Atomics, monitor timeout/reacquisition
  and coalesced event permits complete without errors.
* **Z-02 / X:** Native worker ID/stack/TLS isolation, 64 permit exchanges, checked
  join/close. Record the last stage if it does not return.
* **Z-03 / B:** Deferred native thread ownership/reaper joins after exit and closes.
* **Z-04 / L:** Actual Alias reserve/commit/protect/recommit/query, middle-page
  release, retained canaries and separate SDK/VM reservation ownership succeed.
* **Logs/report:** `zero-services-test.log`, all status/Result lines, launch mode,
  package hash, last action and actual wait. These do not establish Java execution.
* **Exit/recovery:** + closes the application process. Reopen application-mode
  hbmenu afterward. Use HOME/close on a stall and preserve any crash report.

## Z-05 — advanced SafeFetch deliberate-fault probe

* **File/action:** `zero-services-test.nro`, Y, after ordinary A/X/B/L probes
  and exporting their logs. This intentionally faults and may abort or stall.
* **Pass:** Address zero is confirmed unreadable; valid loads pass and actual
  faulting SafeFetch32/N reads return -12345/-67890. If Y returns, run X again
  and report its result before restarting the application process.
* **Evidence:** `zero-services-test.log`, complete crash report if any, last
  stage, actual wait and HOME responsiveness. Emulator/host successes do not
  count as a hardware PASS. HOME/close if stalled.

## J-01 — java-test.nro

* **File:** `java-test.nro`.
* **Installation requirements:** Common setup; miniJVM Java8 class library and bundled two test JARs installed.
* **How to launch:** Common hbmenu launch for the named NRO; the explicitly marked host/future cases are exceptions.
* **Controller operations / actions:** Fresh process, A once.
* **Expected screen/output and successful result:** Hello, arithmetic, exceptions, separate JAR, reflection, thread, allocation, file I/O, static mini bridge, suite PASS and teardown.
* **Failure symptoms:** Missing JAR, exception, hang, leftover java-smoke.txt.
* **Log location:** `java-test.log` under the common log root unless explicitly host/manifest.
* **Information to report:** Every PASS/FAIL line, call_main and shutdown stage.
* **Risk level:** Moderate.
* **Recovery steps:** HOME if active Java hangs; preserve a leftover test file; one run per process.

## J-02 — java-test.nro

* **File:** `java-test.nro`.
* **Installation requirements:** Common setup; Optional trusted Java8 user.jar class UserMain.
* **How to launch:** Common hbmenu launch for the named NRO; the explicitly marked host/future cases are exceptions.
* **Controller operations / actions:** Fresh process, X.
* **Expected screen/output and successful result:** UserMain runs in isolated diagnostic context and returns.
* **Failure symptoms:** Unsupported API/class version/native library, missing JAR or hang.
* **Log location:** `java-test.log` under the common log root unless explicitly host/manifest.
* **Information to report:** Minimal nonsecret Java source, compiler target, first exception.
* **Risk level:** Moderate.
* **Recovery steps:** Remove only the custom JAR for baseline retest; HOME if nonterminating.

## L-01 — minecraft-launcher.nro

* **File:** `minecraft-launcher.nro`.
* **Installation requirements:** Common setup; Owned version JSON/JAR/library/assets under configured root.
* **How to launch:** Common hbmenu launch for the named NRO; the explicitly marked host/future cases are exceptions.
* **Controller operations / actions:** D-pad version, A exports plan; X saves; + relaunch checks persistence.
* **Expected screen/output and successful result:** Real version/inheritance/main/Java/dependency plan; snapshot6 includes Vulkan preference and pinned javaagent; installation remains read only.
* **Failure symptoms:** Parse/cycle/missing-parent errors, unexpected changes, plan claims launchable without backend.
* **Log location:** `minecraft-launcher.log and launch-plan.json` under the common log root unless explicitly host/manifest.
* **Information to report:** Version/parent IDs, nonsecret metadata/config, missing files/natives and blockers.
* **Risk level:** Low.
* **Recovery steps:** Repair a copy on PC; preserve saves; malformed existing config is retained.

## L-02 — minecraft-launcher.nro

* **File:** `minecraft-launcher.nro`.
* **Installation requirements:** Common setup; this particular launcher links the VM-free SDK only.
* **How to launch:** Common hbmenu launch for the named NRO; the explicitly marked host/future cases are exceptions.
* **Controller operations / actions:** L checks actual SDK runtime gate; R opens Vulkan test.
* **Expected screen/output and successful result:** JS_UNAVAILABLE/runtime-not-linked and no game code invoked; no fake Play/success. This expected limitation is BLOCKED for Minecraft.
* **Failure symptoms:** False launch success or a Java8 attempt for classfile69.
* **Log location:** `minecraft-launcher.log` under the common log root unless explicitly host/manifest.
* **Information to report:** Code/stage; report Horizon Minecraft title as NOT ACHIEVED.
* **Risk level:** Low.
* **Recovery steps:** Return to diagnostics; run the separate Java25 NROs first.

## L-03 — minecraft-launcher.nro

* **File:** `minecraft-launcher.nro`.
* **Installation requirements:** Common setup; Isolated copied bad/missing version metadata.
* **How to launch:** Common hbmenu launch for the named NRO; the explicitly marked host/future cases are exceptions.
* **Controller operations / actions:** A inspect error, minus shows recent log, Y diagnostics.
* **Expected screen/output and successful result:** Useful failure and usable menu; saved configuration choices persist only after X.
* **Failure symptoms:** Crash, wrong path, sensitive credential output.
* **Log location:** `minecraft-launcher.log and launch-plan.json` under the common log root unless explicitly host/manifest.
* **Information to report:** Minimal failing JSON, error, menu recovery; never account files.
* **Risk level:** Low.
* **Recovery steps:** Restore fixture on PC; no .minecraft deletion.

## H-01 — Host Java25 reference, no NRO

* **File:** `Host Java25 reference, no NRO`.
* **Installation requirements:** Common setup; Linux X11/Vulkan; game cache outside Git/dist.
* **How to launch:** Common hbmenu launch for the named NRO; the explicitly marked host/future cases are exceptions.
* **Controller operations / actions:** Run tools/snapshot6-reference.py --run-demo; use Continue/Quit as needed.
* **Expected screen/output and successful result:** VULKAN_ONLY_APPLIED, actual Vulkan renderer log, visible snapshot6 Demo title. HOST ONLY PASS; not Switch success.
* **Failure symptoms:** Hash rejection, backend failure, wrong version or no title.
* **Log location:** `Ignored cache host-vulkan.log` under the common log root unless explicitly host/manifest.
* **Information to report:** Renderer/VM versions and explicitly HOST ONLY screenshot.
* **Risk level:** Low to moderate: isolated public demo workload.
* **Recovery steps:** Quit normally; preserve cache/logs; no account token or authentication patch required.

## G-01 — Future Horizon game runtime, no executable provided

* **File:** `Future Horizon game runtime, no executable provided`.
* **Installation requirements:** Common setup; Real Java25 OS/class-library/native/instrumentation port required.
* **How to launch:** Common hbmenu launch for the named NRO; the explicitly marked host/future cases are exceptions.
* **Controller operations / actions:** Do not treat current inspector as a game launcher.
* **Expected screen/output and successful result:** BLOCKED: no title/world on Switch in this release.
* **Failure symptoms:** Any claim of console title from a host image/cross-build.
* **Log location:** `Manifest and implementation status` under the common log root unless explicitly host/manifest.
* **Information to report:** Keep this row BLOCKED until real console evidence exists.
* **Risk level:** Not currently executable.
* **Recovery steps:** Return to independent native tests; runtime source work must precede this test.

## X-01 — All nine NROs

* **File:** `All nine NROs`.
* **Installation requirements:** Common setup; Complete packaged layout and next-load-capable hbmenu.
* **How to launch:** Common hbmenu launch for the named NRO; the explicitly marked host/future cases are exceptions.
* **Controller operations / actions:** Use menu chaining, test + exits; copy all logs after session.
* **Expected screen/output and successful result:** Correct NRO opens, clean exit logs, files readable; no supplied tokens.
* **Failure symptoms:** Wrong next-load path, nonzero Result, missing/corrupt logs.
* **Log location:** `All mc-runtime/logs and dist/manifest.json` under the common log root unless explicitly host/manifest.
* **Information to report:** Source/hashes/launch mode, test sheet and matching crash report.
* **Risk level:** Low.
* **Recovery steps:** Launch each NRO directly if chaining fails; export before rerunning.

## Deferred and legacy coverage

OpenGL context/triangle tests exist on branch legacy/1.12.2 only and are excluded from
mainline. Standard JNI Invocation, Java25 JAR/FFM execution and Minecraft bootstrap
on Horizon require actual execution of the cross-linked VM; do not mark them
passed from the Java8 suite or host title. Fabric/Mixin/world rendering remain
unimplemented.

## Fillable return sheet

Console model: ____ Firmware: ____ Atmosphere: ____ hbmenu: ____

Launch mode: ____ Docked/handheld: ____ Package source/hash: ____

| Case | PASS / FAIL / NOT TESTED / BLOCKED | Last stage / error | Log attached | Notes |
| --- | --- | --- | --- | --- |
| N-01 | NOT TESTED | | | |
| N-02 | NOT TESTED | | | |
| N-03 | NOT TESTED | | | |
| N-04 | NOT TESTED | | | |
| V-01 | NOT TESTED | | | |
| V-02 | NOT TESTED | | | |
| V-03 | NOT TESTED | | | |
| V-04 | NOT TESTED | | | |
| F-01 | NOT TESTED | | | |
| F-02 | NOT TESTED | | | |
| F-03 | NOT TESTED | | | |
| F-04 | NOT TESTED | | | |
| Z-01 | NOT TESTED | | | |
| Z-02 | NOT TESTED | | | |
| Z-03 | NOT TESTED | | | |
| Z-04 | NOT TESTED | | | |
| Z-05 | NOT TESTED | | | |
| J-01 | NOT TESTED | | | |
| J-02 | NOT TESTED | | | |
| J25-01 | NOT TESTED | | | |
| J25-02 | NOT TESTED | | | |
| J25-03 | NOT TESTED | | | |
| J25-04 | NOT TESTED | | | |
| L-01 | NOT TESTED | | | |
| L-02 | NOT TESTED | | | |
| L-03 | NOT TESTED | | | |
| H-01 | NOT TESTED | | | |
| G-01 | BLOCKED | | | |
| X-01 | NOT TESTED | | | |

## Log export / recovery

Copy the entire `sdmc:/switch/mc-runtime/logs/` directory to the PC with the exact
manifest/SHA256SUMS and case sheet. Separate sessions by source revision. Preserve
per-attempt copies before rerunning: most logs append, while snapshot-vulkan.json
and launch-plan.json are overwritten. Preserve
Atmosphere crash reports and the matching `build/<app>.elf`. Symbolicate using
`aarch64-none-elf-addr2line -Cfipe build/<app>.elf <module-relative-PC>`. Report the
last flushed stage and whether HOME responded. Do not send Microsoft credentials,
access tokens, account JSON, console keys or game JARs. The tools request none.

Alternatively, on a computer with Python 3 use the installed helper (replace the
SD path for your system, and write the output outside the SD root):

```sh
python3 /media/switch-sd/switchcraft-docs/collect-feedback.py --sd-root /media/switch-sd --output switchcraft-feedback.zip
```

It copies only the manifest, explicitly named diagnostic/VM logs and snapshot-vulkan.json;
missing entries are listed in collection.json. It never scans .minecraft or
overwrites an output. Review the archive before sharing. Crash reports and
launch-plan.json are excluded: review and attach relevant crash reports manually.
