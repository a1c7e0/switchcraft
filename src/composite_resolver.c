/* Combine the real generated JDK provider and explicitly linked native APIs. */
#include <switchcraft/composite_resolver.h>
#include <switchcraft/native_lookup.h>
#include <javaswitch/native_resolver.h>
#include <string.h>

extern const JsNativeResolver js_openjdk25_native_resolver;

static int app_available(const char *module) {
    if (!module) return 1;
    if (!strcmp(module,"SDL3")) return sc_horizon_native_lookup("SDL3","SDL_Init") != 0;
    if (!strcmp(module,"vulkan")) return sc_horizon_native_lookup("vulkan","vkGetInstanceProcAddr") != 0;
    return 0;
}
static uintptr_t app_resolve(const char *module,const char *name) {
    if (module) return (uintptr_t)sc_horizon_native_lookup(module,name);
    ScNativeFunction fn=sc_horizon_native_lookup("SDL3",name);
    if (!fn) fn=sc_horizon_native_lookup("vulkan",name);
    return (uintptr_t)fn;
}
static int available(const char *module,void *ctx) {
    const JsNativeResolver *jdk=ctx;
    return jdk->module_available(module,jdk->context) || app_available(module);
}
static uintptr_t resolve(const char *module,const char *name,void *ctx) {
    const JsNativeResolver *jdk=ctx;
    uintptr_t found=0;
    if (jdk->module_available(module,jdk->context)) found=jdk->resolve(module,name,jdk->context);
    return found ? found : app_resolve(module,name);
}
int sc_install_composite_resolver(void) {
    const JsNativeResolver *jdk=&js_openjdk25_native_resolver;
    if (jdk->abi_version!=JS_NATIVE_RESOLVER_ABI_VERSION || jdk->struct_size<sizeof(*jdk) ||
        !jdk->module_available || !jdk->resolve) return JS_INCOMPATIBLE;
    /* Fail closed on module-name collision instead of silently mixing providers. */
    if (jdk->module_available("SDL3",jdk->context) || jdk->module_available("vulkan",jdk->context))
        return JS_INCOMPATIBLE;
    JsNativeResolver provider={JS_NATIVE_RESOLVER_ABI_VERSION,sizeof(provider),available,resolve,(void *)jdk};
    return js_native_resolver_install(&provider);
}
