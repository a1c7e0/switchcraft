Switchcraft R4 Device Test Suite

This release provides a reproducible SD-card test package for Switchcraft on Nintendo Switch. It includes nine homebrew applications, a genuine Java 25 runtime image with the pinned ten-module Minecraft profile, diagnostic workloads, and short installation and feedback-collection instructions. The slim SD ZIP is accompanied by matching source and debug-symbol archives; the package manifest records the source revisions, runtime revision, and file hashes.

Validation on Linux

- The complete host suite passed all 91 tests, including the Java SDL/Vulkan/VMA 60-frame run with Khronos validation and the owned-client transformation check.
- The pinned Java runtime suite passed all 22 tests, and the clean-pin runtime source/package verifier passed.
- A fresh JDK 25 run with Mesa llvmpipe 26.4-snapshot-6 visually reached the 26.4-snapshot-6 Demo title using Vulkan. This is host-only evidence.
- Host smoke checks passed for JNI/FFM, FreeType, OpenAL loopback, STB, shaderc, and SPIR-V Cross. The combined Java 25 NRO cross-link has zero undefined symbols and no OpenGL symbols.
- These build and host results do not establish execution on Nintendo Switch hardware. R4 device execution has not been tested.

R3 device context

On R3, physical-device evidence showed that JNI_CreateJavaVM returned, the VM reached vm-ready, and java.base ran class-loading and error paths. The Hello and Java25Smoke classes were missing, the startup agent class was missing, and no JNI/FFM application workload passed. The earlier zero-services-test launch could not be classified because no log or crash capture was supplied. The R4 path fix still requires device confirmation; the zero-services-test launch cause remains unknown.

R4 test order

On device, begin with one fresh java25-test A attempt. If Hello succeeds, continue in separate fresh processes with standalone X and Y, then combined A, X, and Y. Run combined B graphics/VMA, R FreeType/OpenAL loopback, and L native utilities only after the Java prerequisites pass. Follow the included device quickstart and record failures or unsupported results directly. Do not treat host or cross-build results as device passes.

Artifact details

Package size and SHA-256, manifest and SHA256SUMS hashes, source revision, Java-switch revision, and optional asset hashes will be recorded from the final validated artifact bytes before publication.
