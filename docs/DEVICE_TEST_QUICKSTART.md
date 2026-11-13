# Switchcraft first-device checklist

Physical evidence from the R2 package establishes Java 8 diagnostic, private
memory-probe and 300-frame Vulkan presentation passes. Java 25 execution,
JNI/FFM, instrumentation and Minecraft launch remain unachieved on Horizon.
The Linux Java 25 strict-Vulkan Demo title is host-only evidence. The current
Horizon package does not launch Minecraft.

## Install the matching package

Use [the R4 device test-suite release](https://github.com/a1c7e0/switchcraft/releases/tag/test-suite-2026-11-12-r4).
Download `switchcraft-test-suite-2026-11-12-r4.zip` and optionally verify its
SHA-256 in SHA256SUMS. The SD package contains `switch/`, short install
instructions, and manifests/hashes. The matching source companion is a required
separate release asset; debug materials are separate from the SD ZIP.
Read the manifest for the exact java-switch runtime revision. See
[SD_TEST_PACKAGE.md](SD_TEST_PACKAGE.md).

1. Back up the SD card. Extract the test-suite ZIP into its root,
   merging the directories while preserving existing saves and configuration.
   The result must be `SD:/switch/java25-test/java25-test.nro`, not an additional
   wrapper directory. Keep the complete runtime, test JARs and notices; copying
   the NRO files alone is insufficient. The matching source archive is a
   separate required release asset, not part of the SD ZIP.
2. Use Switch 1, Atmosphere and **application-mode hbmenu**. Use your existing
   title-override setup, commonly holding R while starting an installed game.
   Album/applet mode has a different memory budget and is unsuitable for the VM
   baseline. Record the actual mode, firmware, Atmosphere and hbmenu versions.
3. Launch each NRO directly from hbmenu for the first pass. Normal clocks are
   sufficient. No game assets, account credentials or custom JARs are needed
   for the required diagnostics.

## Optional native checks

Diagnostic log names below are under `SD:/switch/mc-runtime/logs/`; Java crash
reports, when present, are in the app folders. Record every raw Result/status
and failed stage. A permission error is useful evidence, not a functional PASS.
These diagnostics are separate from Java 25 and are not prerequisites for Java A.
The R3 `zero-services-test` app was reported unable to start, but no log or
crash capture was supplied. Its cause is unknown. Treat every zero-services
action, including L, as optional and do not let it block the fresh `java25-test`
A attempt. To prioritize the R4 Java sequence, skip to the next section.

| Application | Action | Expected observation | Log |
| --- | --- | --- | --- |
| `switch-diagnostics` | D-pad; A on SD filesystem roundtrip | Responsive menu, write/read/compare PASS, `remove=0` | `switch-diagnostics.log` |
| `switch-diagnostics` | A on Memory report | Process/allocator byte counts and 4 MiB allocation/access/free PASS | Same |
| `switch-diagnostics` | A on Thread create/join | Result 0, `sum=500500`, PASS | Same |
| `java-test` | Fresh process, A once | `DIAGNOSTIC SUITE PASS`, native bridge PASS and `call_main -> 0`; Java 8 diagnostic only | `java-test.log` |
| `ffi-test` | A | Integer downcall 42, mixed downcall 41.5 | `ffi-test.log` |
| `ffi-test` | X, after A passed | Integer upcall 42, mixed upcall 41.5; both close Results 0 | Same |
| `zero-services-test` | L, optional | Private VM mapping reports raw status/Result, protection and canary outcome | `zero-services-test.log` |
| `ffi-test` | Y | Record each step; public physical map may be unsupported (`0xfa01`), which is not a PASS | `ffi-test.log` |
| `ffi-test` | B | Record partial mapping/protection results; unsupported public mapping is not a PASS | Same |
| `zero-services-test` | A | Clock, semaphore, Atomics, monitor and event checks complete without errors | `zero-services-test.log` |
| `zero-services-test` | X | Worker ID/stack/TLS, 64 permit exchanges, join and close succeed | Same |
| `zero-services-test` | B | Deferred worker cleanup/reaper joins after exit and closes successfully | Same |
| `zero-services-test` | L | Private VM memory mapping, permissions, split release and canaries succeed | Same |

R2 device evidence already records Java 8 `DIAGNOSTIC SUITE PASS` and a
successful private-memory L probe, including protection, canaries, split
release and cleanup. `zero-services-test` contains no Java VM. Its **Y** action is an advanced,
deliberate SafeFetch fault test, so run it last, after exporting ordinary probe
logs. Expected fallback values are -12345 and -67890; the process may abort or
stall if recovery fails. If it returns, run X again and retain the result. Keep
any crash report. This is distinct from the non-faulting FFI Y memory test.

## Java 25 device sequence

**Each row requires a new application process.** Do not run A then X/Y inside
the same Java25 session, even if the UI appears to allow it. After a completed
standalone session press +, close/reopen application-mode hbmenu, and launch the
next test. The combined application exits its process after its attempt; that
exit alone does not establish success.

| Application | Action | Pass requires |
| --- | --- | --- |
| `java25-test` | A, fresh process; private L is optional | SDK status 0 / stage `completed`, actual stdout `Hello from Horizon Java 25`, Java major 25 |
| Fresh `java25-test` | X, only if A prints Hello | Stage `completed` and `JAVA25 JNI FFM SUITE PASS` |
| Fresh `java25-test` | Y, only if A prints Hello and X passes | Stage `completed` and `JAVA25_AGENT_SMOKE_PASS` |
| Fresh `switchcraft-java25` | A, only if standalone Java 25 succeeds | Resolver preflight statuses 0, stage `completed`, actual Hello output |
| Fresh `switchcraft-java25` | X, only if combined A succeeds | Preflight passes, stage `completed`, `SWITCHCRAFT_SDL_FFM_PASS SDL_version=` reporting SDL major 3 |
| Fresh `switchcraft-java25` | Y, only if combined X succeeds | Stage `completed`, `SWITCHCRAFT_LWJGL_CORE_PASS SDL_version=...` and `SWITCHCRAFT_LWJGL_VULKAN_FFM_PASS apiVersion=...` |
| Fresh `switchcraft-java25` | B, after standalone and combined A/X/Y pass | Stage `completed`, `PRESENTATION_PASS frames=60`, and VMA allocator initialized/destroyed |
| Fresh `switchcraft-java25` | R, after standalone and combined A/X/Y pass | Stage `completed`, FreeType and OpenAL loopback pass markers; this does not test physical audio output |
| Fresh `switchcraft-java25` | L, after standalone and combined A/X/Y pass | Stage `completed`, STB PNG decode, shaderc compile, SPIR-V Cross reflection and utilities pass markers |

Y uses the instrument profile included in this artifact set. Keep both
`java25-agent-smoke-agent.jar` and `java25-agent-smoke-app.jar` under
`switch/mc-runtime/tests/` and the full pinned Minecraft Java module profile,
including `java.base` and `java.instrument`, under
`switch/mc-runtime/runtimes/openjdk25/`. The manifest lists every image file
and hash; use that inventory rather than assuming a fixed file count. The combined X test also needs
`switchcraft-native-smoke.jar`; it calls linked SDL_GetVersion through JNI and
Java FFM, without creating a window. Combined Y uses the pinned LWJGL 3.4.3
core JAR and linked core JNI provider for its SDL/Vulkan FFM test; no LWJGL
native library is bundled. Run B, R and L as separate fresh processes after
the standalone and combined A/X/Y prerequisites pass. R tests generated PCM
through OpenAL loopback, not the Switch's physical audio output.

R3 physical feedback showed that `JNI_CreateJavaVM` returned and `vm-ready` was
reached, then Hello and Java25Smoke failed because their classes were missing;
the startup agent also failed because its agent class was missing. The combined
app exited without selecting a VM. `zero-services-test` could not launch and no
log was produced. See [the preserved R3 feedback](DEVICE_FEEDBACK_2026_11_12.md).
These observations establish VM creation and `java.base` missing-class handling,
not a successful Java app or workload.

R2's Java 25 A attempts reached heap reservation and then terminated with
`memoryReserver.cpp:521` because the reservation could not protect its
protection page. Java 25 Hello, JNI/FFM, the agent and combined launcher remain
unachieved on hardware. Make one fresh A attempt with R4 and preserve
the generated Java crash report. If A does not print Hello, stop the Java 25
sequence; do not repeat the VM attempt. If A succeeds, continue with fresh
processes in the order above.

On normal return, A leaves the stdout results screen, X leaves stderr, and Y
leaves native status plus process exit result. Use a new application process for
each action. Preserve `java25-test.log` and that attempt's
`java25-vm-<ticks>-stdout.log` / `java25-vm-<ticks>-stderr.log`. Combined runs
use `switchcraft-java25-vm-<ticks>-stdout.log` and
`switchcraft-java25-vm-<ticks>-stderr.log` plus `switchcraft-java25.log`.
Fatal aborts cannot hold a result screen. Preserve fresh relative-PC/register
evidence in logs and any system crash report.

The VM uses a 4 MiB worker stack and pauses UI updates while joining the worker.
There is no established physical-device startup duration or internal VM timeout.
Do not keep pressing buttons to start more attempts. If it stalls, record the
actual wait and last stage, then use HOME and close the application. Preserve
the logs and any crash report before retrying. After a failure, leave dependent
VM rows untested; unrelated graphics/native tests can be reported separately.

## Third pass: graphics and input

These are independent of Java25 title rendering. A successful native test is
not a successful game launch.

| Application | Action | Expected observation |
| --- | --- | --- |
| `vulkan-present` | A | Device/API/features/extensions logged and `snapshot-vulkan.json` written; compatibility requires every base requirement |
| `vulkan-present` | X | Visible changing-color frames, nonzero presented-frame count, no reported Vulkan failure |
| `vulkan-present` | Buttons during X | SDL gamepad name and button IDs/names logged; Plus/SDL Start exits; physical A/SDL East also exits on a paired/Pro controller |
| `vulkan-test` | A, then X | Device enumeration; 4,096 words read back as `0xcafebabe` |
| `vulkan-test` | Y | Offscreen triangle center/corner checks PASS and ASCII preview; this does not test screen presentation |

Export `vulkan-present.log`, `vulkan-present-result.json`, `snapshot-vulkan.json`
and `vulkan-test.log`. R2 completed 300 frames in 5.23 seconds (16.525 ms
average frame turnaround) with clean teardown. Early user exit is incomplete.
The result JSON records elapsed and frame-turnaround timings.
Presentation normally stops after 300 frames or its exit input. If the driver
stalls, use HOME/close and report whether HOME responded. A missing base feature
is a measured compatibility blocker; do not change feature reports to force PASS.

## Graphical launcher and host reference

The complete ZIP already includes the graphical minecraft-launcher. Use its
[UI controls](PRISM_PORT.md) and [launcher checklist](LAUNCHER_TESTS.md) for
version downloads, integrity checks, profiles, import and archive/restore.
L/R changes UI sections; these are not the old inspector's console shortcuts.
The launcher is VM-free and cannot launch Minecraft on Switch. Keep
minecraft-launcher.log and launcher-task-report.json; review an exported
launch-plan.json separately before sharing. Java8 user.jar and arbitrary Mods
are not needed for this checklist. Java/native diagnostic controls are unchanged.

For the separate Linux host title reference, use a Java 25 JDK, X11 display and
working Vulkan driver, plus the built `build/switchcraft-launcher-bridge.jar`:

```sh
python3 tools/snapshot6-reference.py --cache /path/to/host-cache --java /path/to/jdk25/bin/java --run-demo
```

The command verifies/downloads official files into that cache and launches
built-in Demo mode. Select Continue on the accessibility screen if shown.
Confirm `VULKAN_ONLY_APPLIED`, `Using graphics backend Vulkan` in
`host-cache/host-vulkan.log`, and visually confirm the snapshot 6 title before
selecting Quit Game. Keep its screenshot/log explicitly HOST ONLY. See
[HOST_REFERENCE.md](HOST_REFERENCE.md).

## Send results

Most logs append across attempts; `snapshot-vulkan.json`, `launcher-task-report.json` and `launch-plan.json`
are overwritten. Before a repeated case, copy the current files to a uniquely
named PC folder containing case ID, date and package revision. Do not rely on
an appended log as the sole separator between attempts.

Report model, firmware, Atmosphere, hbmenu, application/applet mode,
handheld/docked, controller, package SHA-256, button/action, PASS/FAIL/NOT TESTED,
last stage, actual wait and HOME responsiveness. A useful minimum is the native
baseline plus the first `java25-test` A attempt and its three logs; return a
failure before repeating dependent tests.

With Python 3, collect the allowed diagnostic files into a **new** ZIP outside
the SD root (substitute your mounted SD path):

```sh
python3 /media/switch-sd/switch/mc-runtime/tools/collect-feedback.py --sd-root /media/switch-sd --output switchcraft-feedback-session1.zip
```

The collector includes the manifest, diagnostic/VM logs, profile JSON, unique
VM captures and Java `hs_err_pid*.log` reports from the standalone and combined
Java 25 app folders. It excludes Atmosphere/system crash dumps and
`launch-plan.json`. Do not send game assets, keys or account files. A collected
archive does not certify a test PASS.
