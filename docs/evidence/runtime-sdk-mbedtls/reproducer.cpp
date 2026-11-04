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
