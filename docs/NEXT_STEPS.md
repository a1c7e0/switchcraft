# Next steps

1. Run native input/SD/memory/thread checks, then return vulkan-present base-profile
   JSON and SDL3/VI presentation/gamepad logs from the physical Switch. Preserve
   package hashes, application-mode status, firmware/Atmosphère and crash reports.
2. Run ffi-test integer/mixed downcalls, then W^X upcall closure. A libnx permission
   error is evidence to fix through supported APIs, not permission for patches.
3. Implement the Horizon OpenJDK 25 OS/class-library port. Start Zero plus fallback
   libffi linker, static JNI/FFM registration and a real runtime image. Validate
   Java25Smoke/JNI/FFM against the native runtime; current host passes are a reference.
4. Integrate static LWJGL core/native-library lookup and SDL3/Vulkan/VMA/shaderc/
   SPIR-V Cross/FreeType/OpenAL modules. Existing native SDL/VI success alone does
   not supply the Java bindings. Preserve logs/stages across every increment.
5. Port Java instrumentation/Class-File support for the exact Vulkan-only bridge,
   then execute the same pinned official Demo title sequence on Horizon. No
   authentication bypass or Linux execution substitute. Keep user instance data
   separate and measure native/GPU/Java memory before tuning.
6. Only after the real title/world baseline works, test a real Fabric/Mixin Mod,
   input mappings, audio/network and performance. Do not imply arbitrary Mod
   support from a host reflection or class-loading test.
