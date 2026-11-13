# Snapshot 6 implementation status

Target: **Minecraft 26.4-snapshot-6, Java 25, Vulkan only**. Java runtime work
belongs to the pinned `java-switch` repository. The legacy branch remains
`legacy/1.12.2` at its preserved baseline.

## Current engineering checkpoint

The current Switchcraft engineering checkpoint is dated 2026-11-13. The
R4 package recipe is being updated for the expanded Java profile and native
diagnostics; no R4 SD package has been built, delivered, or published. Current
native exports and cross-link evidence establish build integration only. All
new Horizon execution remains **NOT TESTED**.

| Area | Implemented and built | Host evidence | Horizon evidence |
| --- | --- | --- | --- |
| LWJGL core JNI and lifecycle | 1,957 JNI exports and 2 lifecycle exports in the AArch64 core provider | Real JNI, allocation, FFM and foreign-thread callback tests passed | NOT TESTED |
| SDL3 Java native provider | 1,242 public SDL C function addresses cross-built | Core JNI/SDL resolver and Java presentation tests passed on host | NOT TESTED |
| STB and VMA | 224 STB JNI and 73 VMA JNI exports cross-built | STB Java PNG decode passed; real VMA allocator lifecycle passed with Java graphics | NOT TESTED |
| FreeType and OpenAL | 284 FreeType and 341 OpenAL functions cross-built | FreeType and OpenAL loopback Java smoke passed; loopback is not physical audio output | NOT TESTED |
| Shaderc and SPIR-V Cross | 45 Shaderc and 169 SPVC functions verified in the actual AArch64 archives; cross-link proof passed | Real GLSL-to-SPIR-V compilation and stage-input reflection passed through Java | NOT TESTED |
| SDL/Vulkan/VMA Java graphics smoke | Window, Vulkan surface/swapchain, and VMA initialization succeeded on the host | 60 frames presented on Mesa with validation enabled and no validation errors; explicit count fields fixed | NOT TESTED |
| Java 25 runtime profile | Ten target modules, genuine 577-object management VM and instrument-enabled runtime image/package built | Clean-pin runtime source reconstruction and package verifier passed; final integration pin is being prepared | NOT TESTED |
| Combined Java 25 diagnostic link | Genuine VM/instrumentation plus SDL, FreeType, OpenAL, STB, VMA, Shaderc, and SPIR-V Cross providers | Link passed with zero undefined symbols and no OpenGL symbols; uses baseline runtime `2d53737`, not the pending management image | NOT TESTED |
| Minecraft title on a host | Java 25 strict-Vulkan Demo title visually confirmed under Mesa llvmpipe 25.0.7; HOST ONLY | Full log and screenshot: `docs/evidence/host-2026-11-12/llvmpipe-attempt-02`; game audio disabled because this host had no ALSA sound device. A separate SwiftShader run stopped at an unsupported-feature UI. | NOT ACHIEVED on Switch |
| Minecraft title on Switch | Not implemented as a successful Horizon launch | Host results do not establish this milestone | NOT ACHIEVED |

The ten-module Java profile is being pinned at
`dependencies.lock.json` → `java_switch.runtime_image_modules`. Packaging must
use the runtime image's dynamic path/hash inventory; a fixed file count is not
valid. The combined diagnostic app's new controls are B for SDL/Vulkan and VMA,
R for FreeType/OpenAL loopback, and L for STB, Shaderc, and SPIR-V Cross. Each
requires the standalone and combined A/X/Y prerequisites, with one fresh
application process per action. The combined NRO currently links all listed
native families against the earlier runtime baseline; it does not contain or
validate the updated management VM image.

## Physical-device evidence by package generation

These results are historical and apply only to the binaries identified by
their package manifests.

**B7:** User-supplied 2026-11-08 logs recorded native SD, allocation/thread,
AAPCS64/libffi, service/TLS/reaper/SafeFetch, NVK readback/triangle, snapshot
features, and 300-frame SDL3/VI presentation. The R2 Java 8 diagnostic failed
URI filesystem and exclusive-file checks; those were fixed for R2. Public
physical mapping returned `0xfa01` (unsupported).

**R2:** The Java 8 diagnostic passed; private-memory L passed its tested
protection/canary/split-release/cleanup behavior; Vulkan presentation completed
300 frames in 5.23 seconds with clean teardown. R2 Java 25 attempts entered
heap reservation and failed at `memoryReserver.cpp:521` when the protection page
could not be protected. These are R2-only results.

**R3:** The matching package was
`switchcraft-test-suite-2026-11-09-r3.zip`, with runtime pin
`4d362d4830cfa4e88313dadfcd3a865e826609a5`. Feedback dated 2026-11-12 showed
`JNI_CreateJavaVM` returned, `vm-ready` was reached, and Java 25 `java.base`
class loading/error paths executed. The requested Hello and Java25Smoke classes
were missing, so those workloads did not run. The startup agent stopped because
`AgentSmokeAgent` was missing. No Java application JNI/FFM workload passed; the
combined app did not select a VM. `zero-services-test` was reported unable to
start, without a supplied log or crash capture, so its cause is unknown. See
[the preserved R3 feedback](DEVICE_FEEDBACK_2026_11_12.md) and raw logs.

R3 proves VM creation and limited class-loader execution; it does not prove
successful Hello, JNI, FFM, instrumentation, graphics, or game execution. R4
changes and current cross-builds have no device evidence yet. Use fresh logs
from the exact package and runtime pin to establish any new result.

## Earlier verified Switchcraft baseline

The previously archived clean suite reported 70 Switchcraft tests passed with
one optional owned-client test skipped, and 21 runtime tests passed. Those
counts belong to that archived revision; they do not include the new native
Java diagnostics listed above. Exact results remain in its build logs and
release evidence.

The official client and assets were used only in isolated host caches and were
not committed or included in an SD package. The latest strict-Vulkan title
confirmation is HOST ONLY; it used Mesa llvmpipe and had game audio disabled.
Preserve the distinction between source/cross-build proof, host execution, and
physical-device execution in future status updates.
