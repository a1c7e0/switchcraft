# Snapshot 6 implementation status

Target fixed by the user: **26.4-snapshot-6 / Java 25 / Vulkan only**.
The legacy branch is legacy/1.12.2; Java ownership is the independent java-switch repo.

## Physical evidence status

User-supplied Switch 1 / firmware 21.2.0 logs dated 2026-11-08 came from the
older B7 package, whose package SHA-256 is recorded in
[the device evidence summary](evidence/device-2026-11-08/summary.json). They are
historical hardware results, not validation of R2. That run recorded native SD,
4 MiB allocation and thread checks; AAPCS64/libffi calls; service accounting,
TLS/thread/reaper and SafeFetch probes; NVK readback/triangle; snapshot feature
profile; and SDL3/VI presentation of 300 frames with cleanup. The later 14-frame
presentation ended after a B-button event and the following profile action; no
Vulkan error is logged. These facts do not prove the same binaries in R2.

The older Java 8 diagnostic failed on device URI filesystem paths and exclusive
file creation. The R2 source addresses that failure, but the fix needs a fresh
device run. Public physical-map probes returned `0xfa01`; this is an unsupported
result, not PASS. R2 adds a legitimate private-memory fallback, while its device
protection and budget behavior remains unverified. Standalone and composed Java
25 attempts aborted before VM output with FAR `0x468`; R2 adds retained failure
diagnostics, but startup is still unresolved and requires fresh relative-PC and
register evidence. See runtime issues
[#4](https://github.com/a1c7e0/java-switch/issues/4),
[#5](https://github.com/a1c7e0/java-switch/issues/5) and
[#6](https://github.com/a1c7e0/java-switch/issues/6).

R2 is the complete package `switchcraft-complete-test-suite-2026-11-08-r2.zip`.
Its manifest, not an old short SHA in documentation, is authoritative for each
NRO source and the new java-switch revision. R2 compilation and host tests do
not close any physical case below.

| Milestone | Implemented | Built | Host verification | Horizon hardware |
| --- | --- | --- | --- | --- |
| Switch-style launcher UI and Prism-format instances | First foundation; create/edit/duplicate/check | NRO; console fallback retained | Shared-canvas preview, controller hit targets, instance isolation tests | NOT TESTED |
| Prism component metadata/cache backend | Portable vanilla/LWJGL subset | NRO and host tools | Real snapshot metadata, SHA256 cache, dependency/UTC sorting tests | NOT TESTED |
| Native input/SD/memory/threads | Yes | NRO | Format/link | NOT TESTED |
| NVK transfer/offscreen triangle | Yes | NRO | Format/link | NOT TESTED |
| Exact snapshot feature profile | Yes | NRO/tool | Gate fixtures | NOT TESTED |
| SDL3 Vulkan-only video/input | Yes, patched upstream | Static archive | Link; no GL/EGL API symbols | NOT TESTED |
| Limited SDL/Vulkan static symbol lookup | Yes | AArch64 archive/NRO | Host lookup; linked-symbol check | NOT TESTED |
| VI surface/swapchain/presentation | Yes | NRO | Format/link | NOT TESTED |
| Java 8 interpreter diagnostic | Independent Java repo | NRO/SDK | Real JAR/reflection/thread/I/O/native bridge | NOT TESTED |
| Standard JNI invocation adapter | Yes | SDK / VM diagnostics | Real Java 25 VM/native registration/options/teardown on host | NOT TESTED |
| Java 25 FFM downcalls/upcalls | Adapter/reference tests | Host JAR | PASS on Linux JDK 25 | NOT TESTED |
| libffi AAPCS64/libnx W^X prerequisites | Yes | NRO/SDK | Native link | NOT TESTED |
| Whole-region reserve/commit/uncommit probe | Yes | NRO/SDK | Mocked states/failures | NOT TESTED |
| OpenJDK 25 Horizon VM / JVMTI / instrumentation | Genuine Zero archive and two-module image | Standalone + combined NRO | Cross-link, zero unresolved; host agent/JNI controls PASS | Startup and execution NOT TESTED |
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
