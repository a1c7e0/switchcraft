Runtime revision:
`b7c2ac7fd422bc2543e5c698db4e33a01cc0312d`

Switchcraft revision:
`df342a6ad3b20215ae9d31532c74262115fff3eb`, with uncommitted online installer/download UI integration. The smallest reproducer below uses only the existing ABI-1 SDK and portlibs, so no uncommitted launcher source is needed.

Execution environment:
Host cross-build (Linux x86_64), devkitA64 GCC 15.2.0, libnx 4.12.0, pinned Switchcraft OCI toolchain. Firmware/Atmosphere/application mode: not applicable; no target execution.

Reproduction:
Use Switchcraft's verified extracted ABI-1 SDK in `build/java25-integrated/sdk` (or substitute the same pinned SDK include/archive paths).

```cpp
#include <javaswitch/runtime.h>
#include <mbedtls/sha256.h>
int main() {
    JsRuntimeInfo runtime{};
    js_runtime_query("openjdk25", &runtime);
    mbedtls_sha256_context hash;
    mbedtls_sha256_init(&hash);
    int status=mbedtls_sha256_starts_ret(&hash,0);
    mbedtls_sha256_free(&hash);
    return status+runtime.available;
}

```

```sh
export DEVKITPRO="$PWD/.toolchain/opt/devkitpro"
"$DEVKITPRO/devkitA64/bin/aarch64-none-elf-g++" -std=c++17 -O0 \
  -march=armv8-a+crc+crypto -mtp=soft -fPIE \
  -specs="$DEVKITPRO/libnx/switch.specs" \
  -isystem "$DEVKITPRO/libnx/include" \
  -I"$DEVKITPRO/portlibs/switch/include" -Ibuild/java25-integrated/sdk/include \
  -L"$DEVKITPRO/libnx/lib" -L"$DEVKITPRO/portlibs/switch/lib" \
  -Wl,--gc-sections reproducer.cpp build/java25-integrated/sdk/lib/libjavaswitch.a \
  -Wl,--start-group -lmbedcrypto -lnx -lm -Wl,--end-group -o reproducer.elf
```

No game assets, SD layout, VM options or credentials are required.

Expected behavior:
The public SDK composes with an application's crypto dependency without duplicate private-library exports or mixing incompatible Mbed TLS implementations.

Actual behavior:
The linker exits 1 on duplicate `mbedtls_sha256_*` definitions. It reports the SDK's miniJVM private Mbed TLS implementation and the portlibs implementation as simultaneous strong definitions. Last completed stage: object compilation; no executable produced or VM started.

Evidence:
Complete minimal link output:

```text
/workspace/switchcraft/.toolchain/opt/devkitpro/devkitA64/bin/../lib/gcc/aarch64-none-elf/15.2.0/../../../../aarch64-none-elf/bin/ld: .toolchain/opt/devkitpro/portlibs/switch/lib/libmbedcrypto.a(sha256.o): in function `mbedtls_sha256_init':
sha256.c:(.text.mbedtls_sha256_init+0x0): multiple definition of `mbedtls_sha256_init'; build/java25-integrated/sdk/lib/libjavaswitch.a(sha256.o):/tmp/javaswitch-sdk-pin/.deps/minijvm/utils/https/mbedtls/library/sha256.c:83: first defined here
/workspace/switchcraft/.toolchain/opt/devkitpro/devkitA64/bin/../lib/gcc/aarch64-none-elf/15.2.0/../../../../aarch64-none-elf/bin/ld: .toolchain/opt/devkitpro/portlibs/switch/lib/libmbedcrypto.a(sha256.o): in function `mbedtls_sha256_free':
sha256.c:(.text.mbedtls_sha256_free+0x0): multiple definition of `mbedtls_sha256_free'; build/java25-integrated/sdk/lib/libjavaswitch.a(sha256.o):/tmp/javaswitch-sdk-pin/.deps/minijvm/utils/https/mbedtls/library/sha256.c:88: first defined here
/workspace/switchcraft/.toolchain/opt/devkitpro/devkitA64/bin/../lib/gcc/aarch64-none-elf/15.2.0/../../../../aarch64-none-elf/bin/ld: .toolchain/opt/devkitpro/portlibs/switch/lib/libmbedcrypto.a(sha256.o): in function `mbedtls_sha256_clone':
sha256.c:(.text.mbedtls_sha256_clone+0x0): multiple definition of `mbedtls_sha256_clone'; build/java25-integrated/sdk/lib/libjavaswitch.a(sha256.o):/tmp/javaswitch-sdk-pin/.deps/minijvm/utils/https/mbedtls/library/sha256.c:97: first defined here
/workspace/switchcraft/.toolchain/opt/devkitpro/devkitA64/bin/../lib/gcc/aarch64-none-elf/15.2.0/../../../../aarch64-none-elf/bin/ld: .toolchain/opt/devkitpro/portlibs/switch/lib/libmbedcrypto.a(sha256.o): in function `mbedtls_sha256_starts':
sha256.c:(.text.mbedtls_sha256_starts+0x0): multiple definition of `mbedtls_sha256_starts'; build/java25-integrated/sdk/lib/libjavaswitch.a(sha256.o):/tmp/javaswitch-sdk-pin/.deps/minijvm/utils/https/mbedtls/library/sha256.c:108: first defined here
/workspace/switchcraft/.toolchain/opt/devkitpro/devkitA64/bin/../lib/gcc/aarch64-none-elf/15.2.0/../../../../aarch64-none-elf/bin/ld: .toolchain/opt/devkitpro/portlibs/switch/lib/libmbedcrypto.a(sha256.o): in function `mbedtls_sha256_process':
sha256.c:(.text.mbedtls_sha256_process+0x0): multiple definition of `mbedtls_sha256_process'; build/java25-integrated/sdk/lib/libjavaswitch.a(sha256.o):/tmp/javaswitch-sdk-pin/.deps/minijvm/utils/https/mbedtls/library/sha256.c:183: first defined here
/workspace/switchcraft/.toolchain/opt/devkitpro/devkitA64/bin/../lib/gcc/aarch64-none-elf/15.2.0/../../../../aarch64-none-elf/bin/ld: .toolchain/opt/devkitpro/portlibs/switch/lib/libmbedcrypto.a(sha256.o): in function `mbedtls_sha256_update':
sha256.c:(.text.mbedtls_sha256_update+0x0): multiple definition of `mbedtls_sha256_update'; build/java25-integrated/sdk/lib/libjavaswitch.a(sha256.o):/tmp/javaswitch-sdk-pin/.deps/minijvm/utils/https/mbedtls/library/sha256.c:247: first defined here
/workspace/switchcraft/.toolchain/opt/devkitpro/devkitA64/bin/../lib/gcc/aarch64-none-elf/15.2.0/../../../../aarch64-none-elf/bin/ld: .toolchain/opt/devkitpro/portlibs/switch/lib/libmbedcrypto.a(sha256.o): in function `mbedtls_sha256_finish':
sha256.c:(.text.mbedtls_sha256_finish+0x0): multiple definition of `mbedtls_sha256_finish'; build/java25-integrated/sdk/lib/libjavaswitch.a(sha256.o):/tmp/javaswitch-sdk-pin/.deps/minijvm/utils/https/mbedtls/library/sha256.c:291: first defined here
/workspace/switchcraft/.toolchain/opt/devkitpro/devkitA64/bin/../lib/gcc/aarch64-none-elf/15.2.0/../../../../aarch64-none-elf/bin/ld: .toolchain/opt/devkitpro/portlibs/switch/lib/libmbedcrypto.a(sha256.o): in function `mbedtls_sha256':
sha256.c:(.text.mbedtls_sha256+0x0): multiple definition of `mbedtls_sha256'; build/java25-integrated/sdk/lib/libjavaswitch.a(sha256.o):/tmp/javaswitch-sdk-pin/.deps/minijvm/utils/https/mbedtls/library/sha256.c:83: first defined here
collect2: error: ld returned 1 exit status

```

SDK `libjavaswitch.a` SHA256: `27e7594047fda800671ae9034bbaec7e8a2905391b883bc4398956318d764b94`.
Reproducer SHA256: `049a4b27393859dcb46698e18900ce2c3b9d211557cd9a81d813136140d998d6`.
Link log SHA256: `f97f026bf8b6850e0fbfa60e75ac0eed8d7227458ed430b5926c989fabf03078`.
`java25-test.log`, VM stdout/stderr and crash report: not produced (host link failure; Horizon NOT TESTED).

Analysis:
Confirmed: `nm --defined-only libjavaswitch.a` exposes global `mbedtls_sha256_init/free/clone/starts/process/update/finish/self_test` from the private miniJVM dependency. Requesting the portlibs `_ret` entry pulls its SHA256 object and collides with those SDK exports. No claim is made that either implementation can safely bind against the other's headers/context ABI.
The standalone diagnostic does not reproduce an execution fault: this is a downstream static-link composition defect. Switchcraft's immediate workaround uses libnx SHA1/SHA256 directly, avoiding portlibs Mbed TLS. That workaround does not isolate the SDK's private symbols.

Requested action for java-switch:
Namespace/isolate the SDK's private crypto symbols and their references, or structure SDK archives so unrelated applications can link a separate crypto implementation without ABI collisions. Preserve public SDK ABI 1. Do not use `--allow-multiple-definition` or silently bind incompatible context APIs.
Acceptance: the minimal link above succeeds with both libraries and without duplicate-definition suppression; existing miniJVM/JNI/SDK host regressions and standalone NRO links still pass. This acceptance concerns linking; Horizon execution remains NOT TESTED.
