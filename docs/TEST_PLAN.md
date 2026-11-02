# Physical test plan — snapshot 6 mainline

Every physical case begins as **NOT TESTED**. The Linux Demo title is separate
reference evidence; the Horizon game title remains **BLOCKED / NOT ACHIEVED**.
Use Switch 1, Atmosphere, application-mode hbmenu, normal clocks and supported
libnx APIs. No patches or Linux/Android boot. Keep SD backups and preserve saves
and real configuration when merging the package.

Common installation/launch for each NRO: extract the complete test ZIP to the SD
root and start `sdmc:/switch/<name>/<name>.nro` in application-mode hbmenu, or use
the explicitly named diagnostic next-load action. Logs named below are relative
to `sdmc:/switch/mc-runtime/logs/`. The common prerequisites apply to every case.

First three sessions: N-01 through N-04; V-01 then V-02/03; V-04 then F-01/02.
Proceed to Java8 and launcher checks afterward. A feature-profile PASS is not a
Minecraft title PASS. Standard JNI/FFM host tests are not Horizon runtime tests.

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
* **Controller operations / actions:** During X presentation press ordinary buttons, then Plus/Start.
* **Expected screen/output and successful result:** SDL gamepad name/events appear in log; exit input works.
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
* **Installation requirements:** Common setup; No Horizon Java25 VM supplied in this release.
* **How to launch:** Common hbmenu launch for the named NRO; the explicitly marked host/future cases are exceptions.
* **Controller operations / actions:** L checks actual SDK runtime gate; R opens Vulkan test.
* **Expected screen/output and successful result:** JS_UNAVAILABLE/runtime-not-linked and no game code invoked; no fake Play/success. This expected limitation is BLOCKED for Minecraft.
* **Failure symptoms:** False launch success or a Java8 attempt for classfile69.
* **Log location:** `minecraft-launcher.log` under the common log root unless explicitly host/manifest.
* **Information to report:** Code/stage; report Horizon Minecraft title as NOT ACHIEVED.
* **Risk level:** Low.
* **Recovery steps:** Return to diagnostics; actual Java25 runtime integration is next work.

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

## X-01 — All six NROs

* **File:** `All six NROs`.
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
on Horizon require the missing native VM; do not mark them passed from the Java8
suite or host title. Fabric/Mixin/world rendering remain unimplemented.

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
| J-01 | NOT TESTED | | | |
| J-02 | NOT TESTED | | | |
| L-01 | NOT TESTED | | | |
| L-02 | NOT TESTED | | | |
| L-03 | NOT TESTED | | | |
| H-01 | NOT TESTED | | | |
| G-01 | BLOCKED | | | |
| X-01 | NOT TESTED | | | |

## Log export / recovery

Copy the entire `sdmc:/switch/mc-runtime/logs/` directory to the PC with the exact
manifest/SHA256SUMS and case sheet. Separate sessions by source revision. Preserve
Atmosphere crash reports and the matching `build/<app>.elf`. Symbolicate using
`aarch64-none-elf-addr2line -Cfipe build/<app>.elf <module-relative-PC>`. Report the
last flushed stage and whether HOME responded. Do not send Microsoft credentials,
access tokens, account JSON, console keys or game JARs. The tools request none.
