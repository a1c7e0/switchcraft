# Engineering decisions

1. **Deliver independent NROs first.** Native console diagnostics, GL, NVK,
   Java and metadata inspection are separately launchable. This preserves useful
   tests when a GPU/JVM path fails. Homebrew next-load is a replacement handoff.
2. **Reuse the existing GPU stack.** Stable devkitPro NVC0 for GL; hash-pinned
   public NVK for Vulkan. The heavier Mesa 26 fork is an upgrade candidate after
   hardware evidence. No Vulkan-to-deko3d implementation was invented.
3. **Use an interpreter to obtain a real Java milestone.** The existing OpenJDK
   port is incomplete in this environment. miniJVM can be cross-linked after
   explicit OS adaptation, and its real JAR suite passes on host. This does not
   establish Minecraft, HotSpot, standard JNI or arbitrary Mod compatibility.
4. **Disable unsupported services honestly.** No fake successful mmap, dlopen,
   process creation or JIT stubs. Classic GC uses newlib; unused Immix reservation
   returns ENOSYS. The C11 clock wrapper uses the real realtime clock. TLS entropy
   uses Horizon's CSPRNG; networking itself remains untested.
5. **Protect installations.** The portable planner performs reads only. Actual
   diagnostic writes/config/logs live under `switch/mc-runtime`. Planned game
   directories are isolated; no saves/assets/JARs are modified.
6. **Use semicolon classpaths on Horizon.** `sdmc:` contains a colon. miniJVM's
   parser/property and exported plans use `;`; a future OpenJDK backend must adapt
   its path semantics or normalize paths consistently.
7. **Keep runtime targets distinct.** Java 8 diagnostic, future OpenJDK 8/21/25
   targets and AOT remain separate. Official metadata determines Java requirements;
   no global assumption ties all Minecraft versions to Java 8.
8. **Treat AOT as independent and blocked.** External pz-switch/musl/GraalVM/game
   inputs are absent and licensing is unresolved. No placeholder AOT NRO appears
   in dist. Its build attempts and exact failure are preserved.
9. **Prefer a tested image-extraction fallback on this disk.** Docker works but
   vfs layer copies exhausted space. OCI digests and every layer hash are checked
   while extracting the same official toolchain for local builds.
10. **Keep original code MIT and preserve third-party terms.** Java class-library
    GPL notices/source are distributed with the JAR; native/runtime dependency
    attribution is carried. No game or OptiFine bytes enter release archives.
