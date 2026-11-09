# Snapshot 6 implementation status

Target fixed by the user: **26.4-snapshot-6 / Java 25 / Vulkan only**.
The legacy branch is legacy/1.12.2; Java ownership is the independent java-switch repo.

## Physical evidence status

User-supplied Switch 1 / firmware 21.2.0 logs dated 2026-11-08 came from the
older B7 package, whose package SHA-256 is recorded in
[the device evidence summary](evidence/device-2026-11-08/summary.json). They
record native SD, allocation/thread checks; AAPCS64/libffi calls; service
accounting, TLS/thread/reaper and SafeFetch probes; NVK readback/triangle;
snapshot features; and SDL3/VI presentation of 300 frames with cleanup.

Additional supplied physical logs record R2 results:
the Java 8 diagnostic suite passed, private-memory L passed with protection
round-trip, canaries, split release and clean cleanup, and Vulkan presentation
completed 300 frames in 5.23 seconds at 16.525 ms average turnaround with clean
teardown. These results apply to those R2 binaries. The result and source
manifest for the new R3 SD package must be used to identify its exact runtime
revision; do not carry forward an older pin from documentation.

The older B7 Java 8 diagnostic failed on URI filesystem paths and exclusive file
creation; the R2 Java 8 diagnostic now passes on device. Public physical-map
probes returned `0xfa01`; this is unsupported, not PASS. The R2 private-memory
probe passed its tested protection and cleanup behavior. The R2 Java 25 A
attempts entered heap reservation, then failed with fatal
`memoryReserver.cpp:521` because the protection page could not be protected.
Java 25 execution, JNI/FFM, the agent and combined launcher remain unachieved on
hardware. Use a single fresh R3 Java 25 A attempt after the private L probe; if
it does not print Hello, stop and do not repeat the VM attempt. See runtime issues
[#4](https://github.com/a1c7e0/java-switch/issues/4),
[#5](https://github.com/a1c7e0/java-switch/issues/5) and
[#6](https://github.com/a1c7e0/java-switch/issues/6).

The R3 device package is `switchcraft-test-suite-2026-11-09-r3.zip`. Its
manifest is authoritative for each NRO source and the java-switch revision;
do not carry forward a revision from the older R2 package. Host build and test
results establish only the host-verified cases below.

| Milestone | Implemented | Built | Host verification | Horizon hardware |
| --- | --- | --- | --- | --- |
| Switch-style launcher UI and Prism-format instances | First foundation; create/edit/duplicate/check | NRO; console fallback retained | Shared-canvas preview, controller hit targets, instance isolation tests | NOT TESTED |
| Prism component metadata/cache backend | Portable vanilla/LWJGL subset | NRO and host tools | Real snapshot metadata, SHA256 cache, dependency/UTC sorting tests | NOT TESTED |
| Native input/SD/memory/threads | Yes | NRO | Format/link | Historical B7 native passes; R3 retest pending |
| NVK transfer/offscreen triangle | Yes | NRO | Format/link | NOT TESTED |
| Exact snapshot feature profile | Yes | NRO/tool | Gate fixtures | NOT TESTED |
| SDL3 Vulkan-only video/input | Yes, patched upstream | Static archive | Link; no GL/EGL API symbols | NOT TESTED |
| Limited SDL/Vulkan static symbol lookup | Yes | AArch64 archive/NRO | Host lookup; linked-symbol check | NOT TESTED |
| VI surface/swapchain/presentation | Yes | NRO | Format/link | R2 300-frame PASS, clean teardown |
| Java 8 interpreter diagnostic | Independent Java repo | NRO/SDK | Real JAR/reflection/thread/I/O/native bridge | R2 diagnostic suite PASS |
| Standard JNI invocation adapter | Yes | SDK / VM diagnostics | Real Java 25 VM/native registration/options/teardown on host | NOT TESTED |
| Java 25 FFM downcalls/upcalls | Adapter/reference tests | Host JAR | PASS on Linux JDK 25 | NOT TESTED |
| libffi AAPCS64/libnx W^X prerequisites | Yes | NRO/SDK | Native link | NOT TESTED |
| Public SDK physical map/unmap | Yes | NRO/SDK | Mocked states/failures | B7 raw `0xfa01` Unsupported |
| Private HotSpot reserve/commit/uncommit | Yes | Native L probe | Actual host protection and failure-path tests | R2 L probe PASS; new R3 guard check pending |
| OpenJDK 25 Horizon VM / JVMTI / instrumentation | Genuine Zero archive and two-module image | Standalone + combined NRO | Cross-link, zero unresolved; host agent/JNI controls PASS | R2 startup FAIL during heap initialization; Java/JNI/FFM/agent execution NOT TESTED |
| LWJGL 3.4.3 Horizon identity / JNI load | Upstream platform and Library overrides | Original override JAR | Real LWJGL classes + host fixture | NOT TESTED; FFM SharedLibrary missing |
| Java -> JNI static lookup -> FFM SDL version | Actual JNI callback and real target SDL symbol | Combined NRO and classfile-69 JAR | Host JDK + SDK + native fixture | NOT TESTED |
| Read-only launch planner/SDK gate | Yes | NRO/host inspector | Inheritance/rules/read-only/version/profile | NOT TESTED |
| Strict Vulkan renderer transformation | Yes | Original Java JAR | Synthetic execution + actual snapshot title | VM/instrumentation absent |
| Snapshot 6 Demo title | Reference only | No game NRO | PASS, Linux Java 25 / llvmpipe Vulkan | NOT ACHIEVED |
| Fabric/arbitrary Mods | No | No | No | NOT TESTED |

Main suite: metadata, artifact rejection, exact base profile and real transformed
synthetic renderer behavior. Runtime suite: Java 8 plus Java 25 JNI/FFM/options.
Exact counts/results are in build/host-tests.log and build/java-runtime.log.
No new NRO is claimed to have run on Switch from these host results.

The official client/libraries/assets were hash-verified in isolated host cache,
not tracked/packaged. The first title reference and strict Vulkan reference
have explicit HOST ONLY screenshots/logs under docs/evidence. OpenJDK 25 source
configuration/logs and libffi source/build live in the Java repository. All final
source pins, format verification and hashes are in dist/manifest.json.
