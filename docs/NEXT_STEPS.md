# Next development steps

1. Return the first three hardware results: native platform/SD/memory/thread
   tests, OpenGL context/visible triangle/readback, and NVK enumeration followed
   by fill/readback. Include all logs, launch mode, firmware/Atmosphère versions
   and exact NRO hashes. Do not optimize before these are repeatable.
2. Validate `java-test` on Horizon: initialization, complete suite output, native
   bridge, file cleanup and JVM teardown. If it hangs, use the last stage in the
   flushed log to distinguish pthread/TLS/GC/class-loader failures. Symbolicate
   crash addresses using the matching debug ELF.
3. Exercise Vulkan's offscreen graphics pipeline, then implement VI surface and
   swapchain presentation in a separate test. Record extension/feature/format
   support before comparing modern Minecraft renderer requirements. Preserve the
   working fill/readback path while adding WSI.
4. Reconstruct a pinned, self-contained OpenJDK 8 build: obtain or implement the
   missing runner/POSIX layer, replace developer-local paths, build a real runtime
   image and integrate JNI Invocation in interpreter-only mode first. Test
   exceptions, TLS, threads, reflection, native registration and shutdown before
   enabling JIT/W^X aliases. Java 17/21/25 follow as distinct ports.
5. The 1.12.2 host experiment exposes missing Proxy/UUID/AWT/ImageIO/concurrency
   class-library methods and LWJGL2 natives. Filling these manually is a large
   compatibility project. Prioritize OpenJDK completeness plus a narrowly scoped
   LWJGL/GLFW bridge to the already tested native EGL path. Add input and OpenAL
   only after Java/native method calls and context ownership are stable.
6. Make the launcher enter a compatible runtime in the same process or define a
   serialized NRO handoff with explicit lifecycle and memory budgets. Do not add
   a Play action until it reaches a meaningful verified stage. Keep authentication
   separate, user-controlled and free of credentials in logs.
7. Reproduce AOT only if its missing sources/permissions and legally supplied
   game inputs become available; provide a high-RAM host for the existing image
   command. Keep fixed-image compatibility separate from runtime Mod loading.
8. Add Fabric only after a dynamic loader and bytecode-transforming JVM work.
   A minimal real Mod/Mixin test must pass before claiming support. Keep the
   baseline vanilla milestone intact while adding newer Java/Vulkan versions.
9. Resolve NVK binary-source provenance and rebuild it from a fixed nxvk commit
   before calling the driver build fully source-reproducible. Compare Mesa 26
   fork behavior after hardware baselines are saved.
