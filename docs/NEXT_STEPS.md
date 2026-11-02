# Next steps

1. Run native input/SD/memory/thread checks, then return vulkan-present base-profile
   JSON and SDL3/VI presentation/gamepad logs from the physical Switch. Preserve
   package hashes, application-mode status, firmware/Atmosphère and crash reports.
2. Run ffi-test integer/mixed downcalls, then W^X upcall closure. A libnx permission
   error is evidence to fix through supported APIs, not permission for patches.
3. Await a committed java-switch runtime handoff; review its pinned SDK ABI,
   classfile-69/JNI/FFM results, lifecycle and hardware status. The independent
   Java task owns the OpenJDK/Zero OS and class-library port. Record requests in
   JAVA_INTEGRATION_HANDOFF.md; do not duplicate that port in Switchcraft.
4. Integrate static LWJGL core/native-library lookup and SDL3/Vulkan/VMA/shaderc/
   SPIR-V Cross/FreeType/OpenAL modules. Existing native SDL/VI success alone does
   not supply the Java bindings. Preserve logs/stages across every increment.
5. Integrate the independent runtime's instrumentation/Class-File support with
   the exact Vulkan-only bridge, then execute the pinned Demo title on Horizon. No
   authentication bypass or Linux execution substitute. Keep user instance data
   separate and measure native/GPU/Java memory before tuning.
6. Only after the real title/world baseline works, test a real Fabric/Mixin Mod,
   input mappings, audio/network and performance. Do not imply arbitrary Mod
   support from a host reflection or class-loading test.
