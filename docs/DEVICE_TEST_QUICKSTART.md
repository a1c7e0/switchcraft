# Switchcraft first-device checklist

All Horizon execution below is **NOT TESTED** until physical Switch logs establish
the result. The Linux Java 25 strict-Vulkan Demo title has already been verified;
that host result does not validate these NROs. No Minecraft game launch is
provided by the current Horizon package.

## Install the matching package

Use [the complete SD test-suite release](https://github.com/a1c7e0/switchcraft/releases/tag/test-suite-2026-11-08-r2).
Download the single R2 ZIP and optionally verify its SHA-256 in SHA256SUMS.
It is ready to extract; no split-file assembly is required. It includes the graphical
launcher, all nine NROs and Java/native test resources; there is no overlay. Read
the manifest for the exact new java-switch runtime revision. See
[SD_TEST_PACKAGE.md](SD_TEST_PACKAGE.md).

1. Back up the SD card. Extract the complete test-suite ZIP into its root,
   merging the directories while preserving existing saves and configuration.
   The result must be `SD:/switch/java25-test/java25-test.nro`, not an additional
   wrapper directory. Keep the complete runtime, test JARs, source and notices;
   copying the NRO files alone is insufficient.
2. Use Switch 1, Atmosphere and **application-mode hbmenu**. Use your existing
   title-override setup, commonly holding R while starting an installed game.
   Album/applet mode has a different memory budget and is unsuitable for the VM
   baseline. Record the actual mode, firmware, Atmosphere and hbmenu versions.
3. Launch each NRO directly from hbmenu for the first pass. Normal clocks are
   sufficient. No game assets, account credentials or custom JARs are needed
   for the required diagnostics.

## First pass: native prerequisites

All log names below are under `SD:/switch/mc-runtime/logs/`. Record every raw
Result/status and failed stage. A permission error is useful evidence, not a
functional PASS. Finish the ordinary probes before trying the genuine VM.

| Application | Action | Expected observation | Log |
| --- | --- | --- | --- |
| `switch-diagnostics` | D-pad; A on SD filesystem roundtrip | Responsive menu, write/read/compare PASS, `remove=0` | `switch-diagnostics.log` |
| `switch-diagnostics` | A on Memory report | Process/allocator byte counts and 4 MiB allocation/access/free PASS | Same |
| `switch-diagnostics` | A on Thread create/join | Result 0, `sum=500500`, PASS | Same |
| `java-test` | Fresh process, A once | `DIAGNOSTIC SUITE PASS`, native bridge PASS and `call_main -> 0`; Java 8 diagnostic only | `java-test.log` |
| `ffi-test` | A | Integer downcall 42, mixed downcall 41.5 | `ffi-test.log` |
| `ffi-test` | X, after A passed | Integer upcall 42, mixed upcall 41.5; both close Results 0 | Same |
| `zero-services-test` | L, before public map probes | Private VM mapping reports raw status/Result, protection and canary outcome | `zero-services-test.log` |
| `ffi-test` | Y | Record each step; public physical map may be unsupported (`0xfa01`), which is not a PASS | `ffi-test.log` |
| `ffi-test` | B | Record partial mapping/protection results; unsupported public mapping is not a PASS | Same |
| `zero-services-test` | A | Clock, semaphore, Atomics, monitor and event checks complete without errors | `zero-services-test.log` |
| `zero-services-test` | X | Worker ID/stack/TLS, 64 permit exchanges, join and close succeed | Same |
| `zero-services-test` | B | Deferred worker cleanup/reaper joins after exit and closes successfully | Same |
| `zero-services-test` | L | Private VM memory mapping, permissions, split release and canaries succeed | Same |

`zero-services-test` contains no Java VM. Its **Y** action is an advanced,
deliberate SafeFetch fault test, so run it last, after exporting ordinary probe
logs. Expected fallback values are -12345 and -67890; the process may abort or
stall if recovery fails. If it returns, run X again and retain the result. Keep
any crash report. This is distinct from the non-faulting FFI Y memory test.

## Second pass: genuine Java 25

**Each row requires a new application process.** Do not run A then X/Y inside
the same Java25 session, even if the UI appears to allow it. After a completed
standalone session press +, close/reopen application-mode hbmenu, and launch the
next test. The combined application exits its process after its attempt; that
exit alone does not establish success.

| Application | Action | Pass requires |
| --- | --- | --- |
| `java25-test` | A | SDK status 0 / stage `completed`, actual stdout `Hello from Horizon Java 25`, Java major 25 |
| Fresh `java25-test` | X, after Hello passed | Stage `completed` and `JAVA25 JNI FFM SUITE PASS` |
| Fresh `java25-test` | Y, after X passed | Stage `completed` and `JAVA25_AGENT_SMOKE_PASS` |
| Fresh `switchcraft-java25` | A, after standalone tests passed | Resolver preflight statuses 0, stage `completed`, actual Hello output |
| Fresh `switchcraft-java25` | X, after combined Hello passed | Preflight passes, stage `completed`, `SWITCHCRAFT_SDL_FFM_PASS SDL_version=` reporting SDL major 3 |

Y uses the instrument profile included in this artifact set. Keep both
`java25-agent-smoke-agent.jar` and `java25-agent-smoke-app.jar` under
`switch/mc-runtime/tests/` and the full `java.base`/`java.instrument` image under
`switch/mc-runtime/runtimes/openjdk25/`. The combined X test also needs
`switchcraft-native-smoke.jar`; it calls linked SDL_GetVersion through JNI and
Java FFM, without creating a window.

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
and `vulkan-test.log`. R2 reports PASS only after 300 completed frames; early
user exit is incomplete. The result JSON records elapsed and frame-turnaround
timings.
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
python3 /media/switch-sd/switchcraft-docs/collect-feedback.py --sd-root /media/switch-sd --output switchcraft-feedback-session1.zip
```

The collector includes the manifest, diagnostic/VM logs and profile JSON. It
does not include crash reports or `launch-plan.json`; review and attach relevant
crash reports manually. Do not send game assets, keys or account files. A
collected archive does not certify a test PASS.
