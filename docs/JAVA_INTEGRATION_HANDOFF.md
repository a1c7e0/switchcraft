# Java SDK integration handoff

Switchcraft pins `a1c7e0/java-switch` at
`bff51f38e218af147ca0c9f255fcf1b43be72daf` for the R2 package. The main assistant is authorized
to edit, commit and push java-switch directly. Use an isolated worktree, focused
clean commits and immutable full-SHA references; update this pin only as an
intentional integration change. Actively delegate bounded tasks to `gpt-6-luna`
with `reasoning_effort` set to `high` and disjoint file ownership. The main
assistant reviews changes and runs relevant checks, protecting other agents' work. Switchcraft
owns launcher, LWJGL, SDL/Vulkan and application-native provider integration.
Owner workflow update (2026-11-09): fix runtime defects, validate, commit and
push directly to java-switch. Do not create new issues unless explicitly
requested; issue creation or updates are not a prerequisite. Keep complete
reproduction steps, logs and validation limits in commits/documentation and
validate at immutable SHAs. Existing issue links below are historical references.

R2 physical feedback establishes Java8 diagnostic, private HotSpot memory L and
300-frame Vulkan presentation passes at runtime
`bff51f38e218af147ca0c9f255fcf1b43be72daf`, Switchcraft
`0dc4c1377f81b849e4366c167f0a20177e1fce98`. Java25 A/X/Y all fail during heap
initialization with `memoryReserver.cpp:521`, followed by a secondary heap-report
fault. See [the immutable text evidence and analysis](DEVICE_FEEDBACK_2026_11_09.md).
R3 addresses the real uncommitted guard protection path and guards heap-dependent
fatal reporting until Universe initialization completes. Host tests and genuine
cross-builds do not establish that Java executes on Horizon.

## Historical B7 verified evidence

Linux host Java 25 has reached the 26.4-snapshot-6 title with strict Vulkan;
the screenshot and logs are HOST ONLY. That host result establishes no Horizon Java execution; the physical R2
results above apply only to their identified native/Java8 workloads.

The pinned instrument-enabled OpenJDK 25/Zero archive, ten real provider archives,
`java.base`/`java.instrument` image (7,336 classfile-69 classes), and standalone
`java25-test.nro` were cross-built and verified. `scripts/prepare-java25-runtime.py`
checks artifact and image hashes, SDK ABI 1, actual provider archives and resolver,
then `switchcraft-java25.nro` links the real VM, agent entries, JDK provider and
SDL/Vulkan symbol provider with no undefined symbols. Host JNI/FFM and agent
positive/no-agent-negative controls pass. These are host/build results. Horizon
startup, Hello, JNI, FFM, instrumentation and Minecraft remain NOT TESTED.

The previous pin `698a9a62ccd35f803088abace73ad9c6be5aaa75` encountered two
independent host/build defects. The current pin contains upstream fixes for both;
relative to the previous pin, the runtime source itself is unchanged:

* https://github.com/a1c7e0/java-switch/issues/1 — clean configure required an
  existing build parent; the current pin creates it.
* https://github.com/a1c7e0/java-switch/issues/2 — one host test failed to find a
  valid symlinked JDK cache; the current pin follows the link. Neither issue is
  device evidence.

Upstream documentation revision `534749db60e00feb35d2b7810d683a597aff6cac`
records an independent instrument build at the same `b7c2ac7` pin, starting
without its native build directory and with a symlinked host JDK cache. Its
[immutable evidence](https://github.com/a1c7e0/java-switch/blob/534749db60e00feb35d2b7810d683a597aff6cac/docs/evidence/issues-1-2-clean-instrument.json)
reports 17 host tests and complete workflow/package verification PASS. This
documentation update changes no runtime code or SDK ABI and needs no pin update.
It establishes no Horizon execution result.

The later documentation revision `8e6c732257937fb01108850b2e1e6838d4d33cfd`
adds complete base-profile acceptance at the same pin: 17 host tests, 553 ARM64
VM archive members, java.base and zero missing link symbols, with full package
verification. Its instrument evidence remains 577 members and two modules.
Issues #1 and #2 are now closed for these build defects. These are build/host
results; Horizon startup and execution remain NOT TESTED.

## Contract and lifecycle

`runtime.h` is byte-identical to ABI 1. `js_runtime_query`,
`js_runtime_launch[_with_options]`, `JsRuntimeInfo`, `JsLaunchRequest` and
`JsLaunchResult` are unchanged. The normal SDK/minecraft-launcher is VM-free and
returns `JS_UNAVAILABLE`/`runtime-not-linked`. The separate combined test forces
`JNI_CreateJavaVM` from the actual archive; query availability means symbol
presence only. The runtime verifies Java major 25 after creation and seals the
single resolver before JNI_CreateJavaVM. VM worker/context and function addresses
remain process-resident. The combined test uses application mode, a checked 4 MiB
worker stack, 256 MiB native heap request (loader override wins) and a 128 MiB
Java heap; these are smoke settings, not a Minecraft memory budget. It logs
memory/override and terminates the Horizon process after the attempt.

The generated JDK resolver is composed with exact `SDL3` and `vulkan` module keys
before installation. JDK module collisions fail closed; unknown symbols return
unavailable; global resolution prefers the JDK provider. Callbacks, context and
native addresses are static for process lifetime. Vulkan device/instance methods
must still use actual Vulkan dispatch, not arbitrary global symbol flattening.
The SDK extension is versioned separately as `JS_NATIVE_RESOLVER_ABI_VERSION=1`.

## LWJGL and next handoff

The pinned upstream LWJGL 3.4.3 Platform/Library classes are rebuilt in an
original Horizon override JAR, placed before the official LWJGL classpath entry.
`os.name` remains `Horizon`, architecture `ARM64`; JNI load dispatch delegates
by name to the real JDK loader. The core `lwjgl` JNI provider is not linked and
`SharedLibrary`/FFM adapter explicitly throws, rather than fabricating success.
No Linux library is selected by the override. Host tests exercise original and
patched Platform/Library with a real LWJGL JAR and a host-only JNI fixture.

On physical hardware, run java25-test A, X and Y in fresh application-mode
processes, then switchcraft-java25 A and X in separate fresh processes. X uses
RegisterNatives and Java FFM to call the real linked SDL_GetVersion through the
composed provider. The host test uses a real host JVM and an explicitly host-only
native fixture; it does not establish device behavior. Preserve all VM stdout/stderr, native logs,
firmware/Atmosphere/mode and any crash report; report exact runtime and
Switchcraft SHAs. Do not close a runtime execution issue based on cross-linking.
Next, implement real LWJGL core and FFM SharedLibrary provider bindings, SDL3 and
Vulkan paths, then missing VMA/shaderc/SPIR-V Cross/FreeType/OpenAL/STB/jemalloc
families. Check actual incidentally loaded lwjgl_opengl initialization without
adding an OpenGL renderer. The host title result does not establish Horizon
behavior. On Horizon, attempt the exact snapshot title with owned game files
after real Java/agent/native smoke succeeds.

## Private SDK crypto composition

The online launcher exposed a link collision between the pinned SDK's private
Mbed TLS exports and portlibs libmbedcrypto.
[Issue #3](https://github.com/a1c7e0/java-switch/issues/3) includes the complete
minimal reproduction and link output. The private symbols were isolated in
java-switch `d8ca281fce2b0f21424623bdbdfa77e72ceea08f`; actual SDK builds,
external-crypto target linking and five host regressions passed. That static-link
defect is closed; no Horizon execution result follows. At that checkpoint,
Switchcraft consumed `b7c2ac7` and used libnx SHA APIs independently; the pin
was not silently updated or relabeled. The later R2 integration intentionally
consumes bff51f3 and rebuilt the complete instrument VM/image package.
