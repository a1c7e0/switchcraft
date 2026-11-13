# R4 device feedback received 2026-11-13

The supplied `logs-r4.zip` contains 21 log files. Its SHA-256 is
`eba923eccce8a5c0a3f4a116877623beefcf128553257dc47090ab69dae15836`.
The byte-preserved logs, inventory and checksums are under
[`evidence/device-2026-11-13/`](evidence/device-2026-11-13/summary.json).
These are physical-device observations, distinct from the earlier Linux title
screen and host native-library tests.

## Environment and identity

The logs report firmware 21.2.0 and Application mode (`0`). Atmosphere and
hbmenu versions were not supplied. The combined application reports Switchcraft
`e2b9a7759ec62e9a13667eca15568ea08e00e131`, the R4 source checkpoint.
Its complete A/X/Y/B/R/L menu appears in the log, and all six choices were
selected. The earlier suspicion that its missing on-screen labels indicated
an old combined NRO is therefore excluded by this feedback. The screen itself
was not captured; logging menu text does not prove its readability.

The standalone runtime logs print `2d53737...-dirty`. A source/build audit found
that the direct diagnostic compile paths reused `build/build-info.h` without
refreshing it. The published R4 runtime NROs, VM/JNI archive proofs and
ten-module image hashes are internally consistent with runtime package
`aed255884b8f946a903a4c3d62b2745727f4ef2e`. This is a stale embedded identity
defect, rather than evidence of an old VM archive. The supplied ZIP does not
contain the SD card's NRO files for an independent byte comparison. The next
runtime refreshes its source stamp before both direct diagnostic builds.

## Observed results

| Workload | Actual device result |
| --- | --- |
| `zero-services-test` startup | PASS: native main entry and libnx initialization completed. |
| `zero-services-test` L | PASS for the selected eager C-heap backend: guard bookkeeping, commit/uncommit/recommit, protection round-trip, canaries, middle-page split release, shared SDK/VM reservation ownership and cleanup. Other buttons were not recorded. |
| Standalone A | The real VM reaches `vm-ready`. Native preflight opens the 612-byte Hello JAR with a ZIP signature, but Java cannot find `HelloHorizon25`; SDK status `-103`, stage `main-class`. No Hello execution. |
| Standalone X | VM-ready is reached, but `Java25Smoke` cannot be loaded at the JNI-registration hook. JNI/FFM application tests are not reached. |
| Standalone Y | The application and agent JAR preflights succeed; `AgentSmokeAgent` is not found. JPLIS aborts before a successful premain/transform. |
| Combined A | VM-ready, followed by the same missing Hello class. |
| Combined X/Y/B/R/L | Linked native-symbol preflights pass and VM-ready is reached. `NativeSymbols` is not found, so the ready hook fails before the Java workload. |
| Graphics, VMA, font/audio, shader execution | NOT REACHED. A symbol address preflight is not an API execution pass. |
| Minecraft on Switch | NOT ACHIEVED / NOT TESTED in these logs. |

The zero-services launch and L result are new positive evidence. They do not
establish Java execution, other native-probe results, public physical-map
support, or an explanation for the earlier R3 launch failure.

## Common class-loading defect and next fix

The stderr captures show the intended `sdmc:/...` classpath and semicolon
separator. The failure occurs after native file preflight, before application
classes run. Inspecting the actual OpenJDK loader identifies a separate path
conversion from the earlier NIO `realpath` fix: a file URL uses
`file:/sdmc:/...`, but the Unix `FileURLMapper` passes `/sdmc:/...` to
`JarLoader` as a native filename. The optimized JAR loader bypasses the already
adapted `UnixUriUtils`. Directory classpath loading has the corresponding
`FileLoader` conversion.

The runtime fix translates this local file-URL device root back to `sdmc:/`
when running on Horizon. A regression uses maintained patched OpenJDK loader
classes and real JAR/directory class loading on a host, including a genuine
missing resource. Host results remain host evidence; the corrected binaries
need a fresh physical A attempt. The startup menu also gets an explicit
one-time clear/redraw and flush before input, with every action and source
revision visible. Neither change is claimed device-verified yet.

Begin the next device round with one fresh standalone A. If Hello still fails,
stop dependent VM workloads and export that attempt's native, stdout and stderr
logs. A corrected class-loading test is required before interpreting any
graphics, FFM, audio or shader result.
