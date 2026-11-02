# Physical Switch test plan

Every test starts as **NOT TESTED**. Successful cross-compilation is not a
hardware PASS. Test only Nintendo Switch 1 under Atmosphère/Horizon, without
kernel patches or overclocking. Use application-mode hbmenu. Keep important SD
content backed up and preserve existing saves/configuration when merging the
package. No account credentials or game binaries need to be returned.

The first three sessions should be: (1) HW-01 through HW-05 for native basics,
(2) HW-06/07 for OpenGL, (3) HW-08/09 for NVK enumeration and transfer. Then
try HW-10 graphics and HW-11 onward for Java and launcher metadata.

Common installation for every case: extract the full ZIP to the SD root, retain
its directory structure, verify SHA256SUMS on the PC, and start the NRO under
`sdmc:/switch/<name>/<name>.nro` from application-mode hbmenu (or the explicit
next-load action named in the case). Every log below is relative to
`sdmc:/switch/mc-runtime/logs/`. A log saying PASS reflects what that run measured,
not certification of the complete runtime or game.

## Independent cases

### HW-01 — switch-diagnostics.nro

* **NRO file:** `switch-diagnostics.nro`.
* **Installation requirements:** Common installation; Full SD package; application-mode hbmenu.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Start from hbmenu; press + after observing UI.
* **Expected screen/output and successful result:** Readable diagnostic menu; version and controls visible; return to hbmenu.
* **Failure symptoms:** Black screen, crash, missing entry, or failed exit.
* **Log location:** `switch-diagnostics.log` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** Launch mode, NRO hash, firmware, Atmosphère, exact last screen.
* **Risk level:** Low.
* **Recovery steps:** HOME and relaunch hbmenu; preserve logs.

### HW-02 — switch-diagnostics.nro

* **NRO file:** `switch-diagnostics.nro`.
* **Installation requirements:** Common installation; Handheld Joy-Con or paired Pro Controller.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Use D-pad through all seven entries; A runs selected test; do not press A on GPU entries yet.
* **Expected screen/output and successful result:** Exactly one selection advances per press; handheld and controller buttons work.
* **Failure symptoms:** No input, repeated movement, incorrect action.
* **Log location:** `switch-diagnostics.log` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** Controller model/mode and failing buttons.
* **Risk level:** Low.
* **Recovery steps:** Press + or HOME; reconnect controller and retry.

### HW-03 — switch-diagnostics.nro

* **NRO file:** `switch-diagnostics.nro`.
* **Installation requirements:** Common installation; Writable SD; no existing mc-runtime/diagnostic.tmp.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Select SD filesystem roundtrip, press A.
* **Expected screen/output and successful result:** SD write/read/compare PASS, remove=0; no game files change.
* **Failure symptoms:** Read/write failure, errno, pre-existing temp file preserved.
* **Log location:** `switch-diagnostics.log` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** Exact errno and SD free space/filesystem; preserve any pre-existing temp file.
* **Risk level:** Low.
* **Recovery steps:** Exit; copy logs; inspect temp file before manually removing only a known test leftover.

### HW-04 — switch-diagnostics.nro

* **NRO file:** `switch-diagnostics.nro`.
* **Installation requirements:** Common installation; Application-mode hbmenu; close other homebrew.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Select Memory report and bounded allocation; press A.
* **Expected screen/output and successful result:** Total/used process bytes and malloc arena reported; 4 MiB roundtrip PASS.
* **Failure symptoms:** svcGetInfo errors, allocation failure or inconsistent values.
* **Log location:** `switch-diagnostics.log` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** Raw byte counts, applet type, malloc arena/free values; do not interpret all physical RAM as free heap.
* **Risk level:** Low.
* **Recovery steps:** Exit/relaunch; compare applet mode only as an optional separate report.

### HW-05 — switch-diagnostics.nro

* **NRO file:** `switch-diagnostics.nro`.
* **Installation requirements:** Common installation; Same setup as HW-04.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Select Thread create/join; press A.
* **Expected screen/output and successful result:** threadCreate/start/join result 0; sum=500500 PASS.
* **Failure symptoms:** Nonzero Result, freeze or incorrect sum.
* **Log location:** `switch-diagnostics.log` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** All Result codes and elapsed time to freeze.
* **Risk level:** Low.
* **Recovery steps:** If frozen use HOME; preserve matching ELF/crash report.

### HW-06 — opengl-test.nro

* **NRO file:** `opengl-test.nro`.
* **Installation requirements:** Common installation; Packaged native GL NRO; application-mode hbmenu.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Launch directly or diagnostics OpenGL entry; press A.
* **Expected screen/output and successful result:** EGL and GL API strings/extensions are logged; context succeeds.
* **Failure symptoms:** EGL initialization/context error, black screen or crash.
* **Log location:** `opengl-test.log` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** Last EGL stage/error, GL_VENDOR/RENDERER/VERSION, docked/handheld.
* **Risk level:** Moderate (experimental GPU driver).
* **Recovery steps:** Wait up to 15 seconds; HOME/relaunch if hung; power recovery only if HOME cannot respond.

### HW-07 — opengl-test.nro

* **NRO file:** `opengl-test.nro`.
* **Installation requirements:** Common installation; HW-06 context succeeded.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Press A; observe green triangle on dark blue; B ends graphics early or wait up to 600 frames.
* **Expected screen/output and successful result:** Visible green triangle; center pixel PASS; nonzero frame count; console restored.
* **Failure symptoms:** Wrong colors, no triangle, shader/link error, pixel mismatch, swap error.
* **Log location:** `opengl-test.log` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** Visual result, pixel RGBA, frame count, GL error, whether console returned.
* **Risk level:** Moderate.
* **Recovery steps:** Use B/+ if responsive; otherwise HOME; do not infer success solely from a log without visible output.

### HW-08 — vulkan-test.nro

* **NRO file:** `vulkan-test.nro`.
* **Installation requirements:** Common installation; Packaged NVK NRO; run separately from OpenGL.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Start directly or via diagnostics; press A only.
* **Expected screen/output and successful result:** Physical device and reported API, extensions, features, queues and heaps appear; mode 0 PASS.
* **Failure symptoms:** No devices, missing function, incompatible driver or crash.
* **Log location:** `vulkan-test.log` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** Full log including vendor/device/API/queue/memory data; do not assume conformance.
* **Risk level:** Moderate.
* **Recovery steps:** HOME/relaunch if driver hangs; run native diagnostics independently.

### HW-09 — vulkan-test.nro

* **NRO file:** `vulkan-test.nro`.
* **Installation requirements:** Common installation; HW-08 enumerated a GPU.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Press X once.
* **Expected screen/output and successful result:** GPU queue submission/fence succeed; all 4096 words match 0xcafebabe; PASS.
* **Failure symptoms:** Allocation/bind/submit/fence error, timeout, mismatch or freeze.
* **Log location:** `vulkan-test.log` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** Last API result, mismatch index/value, memory type and timeout behavior.
* **Risk level:** Moderate.
* **Recovery steps:** Timeout path exits; if driver call hangs use HOME; preserve logs before another GPU test.

### HW-10 — vulkan-test.nro

* **NRO file:** `vulkan-test.nro`.
* **Installation requirements:** Common installation; HW-09 passed; this is an offscreen test.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Press Y once.
* **Expected screen/output and successful result:** Shader/pipeline/render pass/submit succeed; green center/dark corner PASS and ASCII triangle.
* **Failure symptoms:** Pipeline/format failure, pixel mismatch, timeout or crash.
* **Log location:** `vulkan-test.log` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** All API results, center/corner pixel values, ASCII output and last stage.
* **Risk level:** Moderate.
* **Recovery steps:** Same recovery as HW-09; report WSI presentation as NOT IMPLEMENTED, not passed.

### HW-11 — java-test.nro

* **NRO file:** `java-test.nro`.
* **Installation requirements:** Common installation; Full package including minijvm_rt.jar and both diagnostic JARs.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Launch via hbmenu or diagnostics; press A once.
* **Expected screen/output and successful result:** jvm_init -> 0, Hello World, suite progresses; hardware JVM initialization may be marked PASS only after seeing these.
* **Failure symptoms:** Missing JAR, initialization error, crash or freeze.
* **Log location:** `java-test.log` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** Last JVM stage, log and elapsed time; no repeated run in same process.
* **Risk level:** Moderate (experimental runtime).
* **Recovery steps:** HOME/relaunch if stuck; preserve logs and matching java-test.elf.

### HW-12 — java-test.nro

* **NRO file:** `java-test.nro`.
* **Installation requirements:** Common installation; Same bundled run as HW-11.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Read suite output after A.
* **Expected screen/output and successful result:** PASS arithmetic, exception handling, separate JAR class loading, reflection invocation and allocation.
* **Failure symptoms:** Missing PASS line, exception trace or nonzero call_main.
* **Log location:** `java-test.log` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** Every PASS/FAIL line, final suite marker, call_main status.
* **Risk level:** Moderate.
* **Recovery steps:** Exit/relaunch; reinstall unchanged bundled JARs if files are missing.

### HW-13 — java-test.nro

* **NRO file:** `java-test.nro`.
* **Installation requirements:** Common installation; Same bundled run; writable runtime instance directory.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Observe Java thread and file tests.
* **Expected screen/output and successful result:** Thread start/join, file creation/read/write/cleanup PASS; no java-smoke.txt remains.
* **Failure symptoms:** Thread hang, I/O exception, existing test file or failed cleanup.
* **Log location:** `java-test.log` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** File path/error, leftover file content only if it is the original test file, last thread stage.
* **Risk level:** Low to moderate.
* **Recovery steps:** HOME if hung; preserve a leftover file before manually deleting a confirmed test artifact.

### HW-14 — java-test.nro

* **NRO file:** `java-test.nro`.
* **Installation requirements:** Common installation; Same bundled run.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Observe nativeAdd result and teardown.
* **Expected screen/output and successful result:** PASS miniJVM static native bridge; DIAGNOSTIC SUITE PASS; JVM teardown completed.
* **Failure symptoms:** Missing bridge/teardown, unresolved method, crash; standard JNI Invocation remains BLOCKED.
* **Log location:** `java-test.log` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** Bridge result, suite marker, teardown stage; do not label standard JNI as supported.
* **Risk level:** Moderate.
* **Recovery steps:** Exit/relaunch; retain native crash addresses for addr2line.

### HW-15 — java-test.nro

* **NRO file:** `java-test.nro`.
* **Installation requirements:** Common installation; Optional trusted Java 8 user.jar defining UserMain.main.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Put tests/user.jar under mc-runtime; fresh NRO launch; press X once.
* **Expected screen/output and successful result:** UserMain executes from JAR with isolated directory argument and returns.
* **Failure symptoms:** Unsupported Java API/class version/native dependency, missing JAR or hang.
* **Log location:** `java-test.log` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** Minimal source, compiler target and first exception; do not send credentials.
* **Risk level:** Moderate.
* **Recovery steps:** Use HOME if custom Java code hangs; remove only the custom user.jar before baseline retest.

### HW-16 — minecraft-launcher.nro

* **NRO file:** `minecraft-launcher.nro`.
* **Installation requirements:** Common installation; Legitimate local versions/<id>/<id>.json under configured root.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Launch inspector; select version with D-pad; press A.
* **Expected screen/output and successful result:** Installed JSONs listed; selected version/main class/Java requirement and dependency counts reported.
* **Failure symptoms:** No scan results, malformed JSON error or wrong inherited JAR.
* **Log location:** `minecraft-launcher.log and launch-plan.json` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** Root, version ID, redacted version metadata, counts and exact error; no account files/tokens.
* **Risk level:** Low (read-only game data).
* **Recovery steps:** Fix metadata/import on PC; game directory should remain unchanged.

### HW-17 — minecraft-launcher.nro

* **NRO file:** `minecraft-launcher.nro`.
* **Installation requirements:** Common installation; At least one inherited version or Fabric-installed metadata, without claiming Mod support.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Select inherited version and press A.
* **Expected screen/output and successful result:** Plan resolves parents, Maven overrides and arguments; marks native/runtime blockers; launchable=false.
* **Failure symptoms:** Inheritance error, cycle message, missing parent or unexpected native desktop classpath.
* **Log location:** `launch-plan.json` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** Parent chain, selected JAR, skipped libraries/native substitutions and unresolved placeholders.
* **Risk level:** Low.
* **Recovery steps:** Repair a copy of metadata on PC; never alter saves to fix this test.

### HW-18 — minecraft-launcher.nro

* **NRO file:** `minecraft-launcher.nro`.
* **Installation requirements:** Common installation; Writable config directory; retain existing launcher.json backup on PC.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Use L/R to choose targets; X saves; + exits; relaunch.
* **Expected screen/output and successful result:** Chosen version/runtime/graphics persist; example file never replaces real config.
* **Failure symptoms:** Save error, lost choice, malformed config warning; existing malformed config must be preserved.
* **Log location:** `minecraft-launcher.log and config/launcher.json` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** Saved nonsecret configuration and exact error; note that heap is planning only.
* **Risk level:** Low.
* **Recovery steps:** Restore backed-up config or edit a valid JSON; do not delete .minecraft.

### HW-19 — minecraft-launcher.nro

* **NRO file:** `minecraft-launcher.nro`.
* **Installation requirements:** Common installation; Installation missing a JAR or deliberately invalid copied JSON in an isolated test root.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Press A; then navigate menu and use minus to view recent log.
* **Expected screen/output and successful result:** Useful stage/error and blockers; application remains usable; no game execution; no token prompt.
* **Failure symptoms:** Crash, unreadable error or launchable=true without a backend.
* **Log location:** `minecraft-launcher.log and launch-plan.json` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** Minimal failing metadata, error text and menu recovery behavior.
* **Risk level:** Low.
* **Recovery steps:** Restore test fixture; return to diagnostics or exit normally.

### HW-20 — switch-diagnostics.nro

* **NRO file:** `switch-diagnostics.nro`.
* **Installation requirements:** Common installation; All packaged paths unchanged; next-load-capable hbmenu.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Select each other NRO; B returns from GL/Vulkan/Java; Y returns from inspector.
* **Expected screen/output and successful result:** Requested NRO opens; original process exits; missing NRO reports error and menu survives.
* **Failure symptoms:** envSetNextLoad error, wrong path, hbmenu return instead of handoff.
* **Log location:** `Relevant application logs` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** Exact next-load Result, installation path and hbmenu version.
* **Risk level:** Low.
* **Recovery steps:** Launch NROs directly if next-load is unsupported.

### HW-21 — minecraft-launcher.nro

* **NRO file:** `minecraft-launcher.nro`.
* **Installation requirements:** Common installation; Select any real version; no credentials needed.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Press A to reach the Minecraft preflight boundary.
* **Expected screen/output and successful result:** Plan records launchable=false and exact missing runtime/native/authentication placeholders. Mark real Minecraft bootstrap BLOCKED on Horizon.
* **Failure symptoms:** Any false Play/success claim, token logging or unexpected game-directory writes.
* **Log location:** `launch-plan.json` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** Blocker list; distinguish this preflight from the separate failed host bootstrap experiment.
* **Risk level:** Low.
* **Recovery steps:** Exit; retain plan; actual bootstrap awaits a compatible JVM/LWJGL backend.

### HW-22 — all five NROs

* **NRO file:** `all five NROs`.
* **Installation requirements:** Common installation; After a normal successful and failed test; SD readable on PC.
* **How to launch:** Common hbmenu launch for the named NRO; follow the specific handoff if given.
* **Controller operations:** Press + from menus, then copy entire logs/ directory to PC.
* **Expected screen/output and successful result:** Return to hbmenu, Clean exit lines, logs readable; no supplied access tokens.
* **Failure symptoms:** Hang on exit, corrupted/missing log or sensitive content.
* **Log location:** `All logs and matching dist/manifest.json` under the common logs directory (configuration paths are outside logs as named).
* **Information to report:** NRO hashes, launch mode, PASS/FAIL/NOT TESTED/BLOCKED table and relevant crash reports.
* **Risk level:** Low.
* **Recovery steps:** HOME/relaunch if needed; copy logs before rerunning to preserve evidence.

## Deferred capabilities

Standard `JNI_CreateJavaVM`/JNI Invocation, OpenJDK initialization, Vulkan
swapchain presentation, Minecraft title-screen/world rendering and Fabric Mod
loading are **BLOCKED / NOT IMPLEMENTED**, not hardware test passes. HW-14 tests
miniJVM's custom static bridge only. HW-21 tests graceful Minecraft preflight
failure. Do not create fake pass results for unavailable features.

## Returnable result sheet

Console model/revision: ______  Firmware: ______  Atmosphère: ______

hbmenu version: ______  Launch mode: ______  Docked/handheld: ______

Package source revision: ______  SHA256SUMS verified: ______

| Test ID | PASS / FAIL / NOT TESTED / BLOCKED | Last stage / error | Log attached | Notes |
| --- | --- | --- | --- | --- |
| HW-01 | NOT TESTED | | | |
| HW-02 | NOT TESTED | | | |
| HW-03 | NOT TESTED | | | |
| HW-04 | NOT TESTED | | | |
| HW-05 | NOT TESTED | | | |
| HW-06 | NOT TESTED | | | |
| HW-07 | NOT TESTED | | | |
| HW-08 | NOT TESTED | | | |
| HW-09 | NOT TESTED | | | |
| HW-10 | NOT TESTED | | | |
| HW-11 | NOT TESTED | | | |
| HW-12 | NOT TESTED | | | |
| HW-13 | NOT TESTED | | | |
| HW-14 | NOT TESTED | | | |
| HW-15 | NOT TESTED | | | |
| HW-16 | NOT TESTED | | | |
| HW-17 | NOT TESTED | | | |
| HW-18 | NOT TESTED | | | |
| HW-19 | NOT TESTED | | | |
| HW-20 | NOT TESTED | | | |
| HW-21 | NOT TESTED | | | |
| HW-22 | NOT TESTED | | | |

## Log export and crash analysis

After each session, copy the entire `sdmc:/switch/mc-runtime/logs/` directory and
`dist/manifest.json` into one folder on your PC. Keep logs from different package
revisions separate. For a crash, also preserve the Atmosphère crash report and
the matching `build/<application>.elf`; developers can use
`aarch64-none-elf-addr2line -Cfipe build/<application>.elf <module-relative-PC>`.
Report the last flushed stage and whether HOME still responded. Never include
Microsoft credentials, access tokens, `launcher_accounts.json`, console keys,
or game JARs in a bug report. The provided code does not request them.
