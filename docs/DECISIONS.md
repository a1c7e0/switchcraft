# Decisions for mainline

1. Preserve the complete previous source milestone on branch 1.12.2 and push it.
   Main targets the exact user-selected snapshot 6, not a moving latest alias.
2. Separate runtime ownership into java-switch. Consume a full commit, versioned
   C SDK and its standalone artifacts; preserve Java-8 diagnostics while porting
   Java 25. A Java version mismatch must fail before executing bytecode.
3. Reuse the existing SDL3 Switch/NVK port. Patch its unconditional EGL/window
   references and build without GL/EGL. No new Vulkan-to-deko3d layer was created.
4. Read real snapshot classes/metadata. Implement exact base features, SDL/VI
   presentation and gamepad tests; do not infer compatibility from device count.
5. The client retains GL fallback. Use an original hash-pinned single-method
   transformation through Java 25's public Class-File API and instrumentation.
   Preserve the normal game class loader; the custom-loader experiment failed.
   No authentication changes, feature fakes or game bytecode redistribution.
6. Establish a host title reference to validate actual game requirements and
   transformation behavior. Label its Linux/software Vulkan screenshot HOST ONLY;
   it does not satisfy the Horizon title objective or substitute streaming.
7. Port actual prerequisites. The same standard JNI adapter passes host Java-25
   and FFM tests. Zero has a libffi fallback linker, so add real AAPCS64 and libnx
   W^X closure code. Do not claim this is a complete OpenJDK 25 OS port.
8. Keep graphics/runtime native tests independent, with finite acquire/fence
   waits, per-image present semaphores and explicit process-exit behavior after
   pending GPU work. Driver-level hangs still need physical diagnosis.
9. Keep .minecraft read only. Runtime config/logs/test instances remain separate;
   installed saves and real configuration are never shipped/overwritten.
