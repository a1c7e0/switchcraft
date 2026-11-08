# R2 device-feedback test package

Download ONE finished SD-root ZIP from https://github.com/a1c7e0/switchcraft/releases/tag/test-suite-2026-11-08-r2 . No user-facing split assembly is required.

This branch stores exact ZIP transport parts below GitHub Git blob limits. RELEASE_INPUTS.json pins ordering, hashes, source and runtime identities. Actions verifies and publishes the single finished ZIP. Matching debug ELFs are included separately; corresponding source/notices are inside the SD ZIP.

New Java8 filesystem fixes, private eager heap-backed data memory, persistent result review, unique VM output, relative-PC/register fatal capture, smoother Vulkan color and input/teardown reports are cross-built/host-tested. New device execution is NOT TESTED. The original Java25 crash cause is not established; do not infer success from a cross-link. Historical B7 native/FFI/SafeFetch/Vulkan results remain separate.

Runtime issues: https://github.com/a1c7e0/java-switch/issues/4 https://github.com/a1c7e0/java-switch/issues/5 https://github.com/a1c7e0/java-switch/issues/6 https://github.com/a1c7e0/java-switch/issues/7 .
