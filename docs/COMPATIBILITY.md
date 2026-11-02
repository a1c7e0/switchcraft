# Compatibility

## Evidence vocabulary

**Supported** means the stated host behavior was exercised. **Experimental**
means implementation and cross-build exist but Switch execution is NOT TESTED.
**Not implemented** means there is no execution path. **Incompatible** denotes
a known requirement mismatch. No listed Minecraft version is playable here.

| Component | Current status | Evidence |
| --- | --- | --- |
| Horizon diagnostics | Experimental | Genuine AArch64 NRO, host format checks |
| Mesa NVC0 EGL/OpenGL | Experimental | Real static driver linked; context/triangle implementation |
| Mesa NVK | Experimental, nonconformant Maxwell | Real static driver linked; enumeration/fill/offscreen pipeline implementation |
| Vulkan presentation | Not implemented | No surface/swapchain/render-to-display path |
| Zink | Not implemented | No Zink library linked |
| miniJVM Java 8 interpreter | Host-tested; Horizon experimental | Same diagnostic adapter executes real JARs on host |
| Standard JNI Invocation / HotSpot | Not implemented | No `JNI_CreateJavaVM` backend linked |
| Minecraft metadata planning | Supported on host; Horizon experimental | Synthetic inheritance/rules tests and real official version JSONs |
| LWJGL/GLFW/OpenAL for Java | Not implemented | Host Minecraft experiment fails at LWJGL initialization |
| Fabric/Mixin | Not implemented | No Mod loading/transformer test |

## Minecraft versions

These requirements come from the exact official JSON files retained in
`docs/evidence/official-metadata/`; their SHA-256 values and plan counts are in
`docs/evidence/official-version-plans.json`. No game JAR is distributed.

| Version | Metadata Java | Java native ecosystem | Progress / failure stage |
| --- | --- | --- | --- |
| 1.12.2 | 8 (`jre-legacy`) | LWJGL 2, Paulscode audio/JInput | Official JSON parsed; isolated host bytecode bootstrap reached `Main.main`, failed at LWJGL `Sys` with missing native/AWT methods and `IncompatibleClassChangeError` |
| 1.16.5 | 8 (`jre-legacy`) | LWJGL 3 / GLFW / OpenAL | JSON and dependency/argument planning only; native runtime integration blocked |
| 1.20.1 | 17 (`java-runtime-gamma`) | LWJGL 3 / GLFW / OpenAL | Metadata only; Java 17 Horizon runtime absent |
| 1.21.1 | 21 (`java-runtime-delta`) | LWJGL 3 / GLFW / OpenAL | Metadata only; Java 21 Horizon runtime absent |
| 26.4-snapshot-6 | 25 (`java-runtime-epsilon`) | LWJGL 3.4.3, including Vulkan bindings | Metadata only; Java 25, required Vulkan feature set, presentation and JNI unverified |

Version manifests identify library families, not all required OpenGL/Vulkan
features. A linked `lwjgl-vulkan` JAR does not prove that this GPU can run its
renderer. Exact graphics requirements for each client must be checked against
legitimate client/source evidence and physical-device feature reports.

Minecraft heap, native memory, driver allocations and achievable frame rates
have not been measured. The Switch's physical 4 GB is not a usable application
heap guarantee. Use process-limit and allocation reports from the real console.
Fabric's dynamic class loading, bytecode rewriting and Mixin hooks are not
validated by a simple JAR/reflection test. Arbitrary Mod support is not claimed.
