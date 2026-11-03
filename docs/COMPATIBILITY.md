# Compatibility

| Target | Required runtime | Renderer/input | Actual state |
| --- | --- | --- | --- |
| 26.4-snapshot-6 | Java 25 / classfile 69 | Vulkan 1.2 base, SDL3/gamepad | Strict Vulkan Demo title on host; Horizon VM missing |
| Java 25 JNI/FFM workload | Java 25 | Native downcalls/upcalls | Genuine Zero VM cross-linked; host adapter passes; Horizon execution NOT TESTED |
| miniJVM diagnostic | Java 8 | Console | Host passed; Horizon NRO untested |
| Legacy Minecraft experiments | Java 8/17/21 metadata targets | Historical OpenGL/LWJGL | Preserved on branch legacy/1.12.2 |

Mainline does not offer OpenGL selection. The original snapshot client still has
an OpenGL fallback; the hash-pinned bridge restricts renderer selection to one
Vulkan backend. Native SDL3 is compiled without GL/EGL. The inspected controller
path is SDL3, not the old GLFW path. Joy-Con/Pro Controller behavior needs hardware
SDL event tests before claiming in-game support.

profiles/26.4-snapshot-6.json records the actual base requirements read from
SHA-1-verified client bytecode: API 1.2; KHR synchronization2/swapchain and EXT
vertex_attribute_divisor; multiDrawIndirect, drawIndirectFirstInstance,
samplerAnisotropy, shaderDrawParameters, timelineSemaphore, hostQueryReset,
synchronization2 and vertexAttributeInstanceRateDivisor. This is a base profile,
not full device/shader/presentation conformance. Real limits and optional feature
paths remain measured integration work.

The Switch's shared physical 4 GB is not an application heap guarantee. No usable
game heap, world performance, frame rate, audio or network compatibility has been
measured. Default-user-jvm metadata is retained but not applied as a memory policy.
Standard JNI/FFM and bytecode instrumentation on host are not Fabric validation;
no real Mod/Mixin has been loaded on the Switch.
