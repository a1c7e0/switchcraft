# Snapshot 6 implementation status

Target fixed by the user: **26.4-snapshot-6 / Java 25 / Vulkan only**.
The legacy branch is legacy/1.12.2; Java ownership is the independent java-switch repo.

| Milestone | Implemented | Built | Host verification | Horizon hardware |
| --- | --- | --- | --- | --- |
| Native input/SD/memory/threads | Yes | NRO | Format/link | NOT TESTED |
| NVK transfer/offscreen triangle | Yes | NRO | Format/link | NOT TESTED |
| Exact snapshot feature profile | Yes | NRO/tool | Gate fixtures | NOT TESTED |
| SDL3 Vulkan-only video/input | Yes, patched upstream | Static archive | Link; no GL/EGL API symbols | NOT TESTED |
| VI surface/swapchain/presentation | Yes | NRO | Format/link | NOT TESTED |
| Java 8 interpreter diagnostic | Independent Java repo | NRO/SDK | Real JAR/reflection/thread/I/O/native bridge | NOT TESTED |
| Standard JNI invocation adapter | Yes | SDK | Real Java 25 VM/native registration/options/teardown | No VM linked |
| Java 25 FFM downcalls/upcalls | Adapter/reference tests | Host JAR | PASS on Linux JDK 25 | NOT TESTED |
| libffi AAPCS64/libnx W^X prerequisites | Yes | NRO/SDK | Native link | NOT TESTED |
| Whole-region reserve/commit/uncommit probe | Yes | NRO/SDK | Mocked states/failures | NOT TESTED |
| OpenJDK 25 Horizon VM | OS port not implemented | NO | Configure attempted, unsupported OS elf | NOT AVAILABLE |
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
