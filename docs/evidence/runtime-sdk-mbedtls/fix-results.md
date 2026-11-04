Fixed and pushed in **d8ca281fce2b0f21424623bdbdfa77e72ceea08f**. Public ABI-1 runtime.h is byte-identical. The SDK build derives and namespaces private Mbed TLS definitions and references; no duplicate-definition suppression is used.

Validation:
- Actual isolated Horizon and host SDK builds passed, isolating 712 and 717 private symbols.
- The issue reproducer linked against the actual newly built SDK plus portlibs libmbedcrypto with exit status 0; target is AArch64 PIE. Full link output is empty (no errors/warnings).
- Horizon SDK SHA256: bf8ade0016635021e7ac9da8209dc3d0a32cdd0c3e26ceb0601195c5c71c74b9.
- Five host tests passed: composition/public-symbol/idempotence regression, real interpreter suite and loader guards, runtime refusal gates, JNI/JVM/FFM invocation.
- Temporary archive publication now occurs beside the archive to avoid cross-filesystem EXDEV on replacement.

The complete instrument VM/image package was not rebuilt for this SDK-only change. No Horizon execution occurred; Java, JNI/FFM, instrumentation and Minecraft execution on Switch remain NOT TESTED. Switchcraft still pins b7c2ac7 and independently avoids the old conflict using libnx SHA APIs. Consuming the new SDK requires an intentional immutable pin update and package build.

Fixed reproducer ELF SHA256: f35f851b50136f3c2594aacdd0733104a68b9bcbbdcfde15c5b17c66713cc304.
