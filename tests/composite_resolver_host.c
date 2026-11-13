#include <switchcraft/composite_resolver.h>
#include <switchcraft/native_lookup.h>
#include <javaswitch/native_resolver.h>
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
static int jdk_add(int a,int b){return a+b;}
static int app_mul(int a,int b){return a*b;}
static void marker(void){}
static int jdk_module(const char *m,void *ctx){(void)ctx;const char *collision=getenv("SC_TEST_COLLISION");return !m || !strcmp(m,"java") || (collision && !strcmp(m,collision));}
static uintptr_t jdk_lookup(const char *m,const char *n,void *ctx){(void)ctx;return (!m||!strcmp(m,"java"))&&!strcmp(n,"jdk_add")?(uintptr_t)jdk_add:0;}
const JsNativeResolver js_openjdk25_native_resolver={JS_NATIVE_RESOLVER_ABI_VERSION,sizeof(JsNativeResolver),jdk_module,jdk_lookup,0};
int sc_lwjgl_core_available(const char *m){return !m || !strcmp(m,"lwjgl");}
uintptr_t sc_lwjgl_core_lookup(const char *m,const char *n){return (!m||!strcmp(m,"lwjgl"))&&!strcmp(n,"core_marker")?(uintptr_t)marker:0;}
int sc_lwjgl_utilities_available(const char *m){return m&&(!strcmp(m,"lwjgl_stb")||!strcmp(m,"lwjgl_vma"));}
uintptr_t sc_lwjgl_utilities_lookup(const char *m,const char *n){return sc_lwjgl_utilities_available(m)&&!strcmp(n,"utility_marker")?(uintptr_t)marker:0;}
int sc_font_audio_available(const char *m){return m&&(!strcmp(m,"freetype")||!strcmp(m,"openal"));}
uintptr_t sc_font_audio_lookup(const char *m,const char *n){return sc_font_audio_available(m)&&!strcmp(n,"font_audio_marker")?(uintptr_t)marker:0;}
int sc_shader_libraries_available(const char *m){return m&&(!strcmp(m,"shaderc")||!strcmp(m,"spirv-cross-c"));}
uintptr_t sc_shader_libraries_lookup(const char *m,const char *n){return sc_shader_libraries_available(m)&&!strcmp(n,"shader_marker")?(uintptr_t)marker:0;}
ScNativeFunction sc_horizon_native_lookup(const char *m,const char *n){
    if(!m||!n)return 0;
    if(!strcmp(m,"SDL3")&&!strcmp(n,"SDL_Init"))return marker;
    if(!strcmp(m,"vulkan")&&!strcmp(n,"vkGetInstanceProcAddr"))return marker;
    if(!strcmp(m,"SDL3")&&!strcmp(n,"app_mul"))return (ScNativeFunction)app_mul;
    return 0;
}
int main(void){
    uintptr_t p=42;int available=0;
    if(getenv("SC_TEST_COLLISION")){
        assert(sc_install_composite_resolver()==JS_INCOMPATIBLE);
        assert(js_native_module_available(getenv("SC_TEST_COLLISION"),&available)==JS_UNAVAILABLE&&!available);
        return 0;
    }
    assert(sc_install_composite_resolver()==JS_OK);
    assert(js_native_module_available("java",&available)==JS_OK&&available);
    assert(js_native_module_available("SDL3",&available)==JS_OK&&available);
    assert(js_native_module_available("lwjgl",&available)==JS_OK&&available);
    assert(js_native_symbol_lookup("lwjgl","core_marker",&p)==JS_OK&&p==(uintptr_t)marker);
    assert(js_native_symbol_lookup(NULL,"core_marker",&p)==JS_OK&&p==(uintptr_t)marker);
    assert(js_native_symbol_lookup("lwjgl","app_mul",&p)==JS_UNAVAILABLE&&p==0);
    assert(js_native_symbol_lookup("lwjgl_stb","utility_marker",&p)==JS_OK&&p==(uintptr_t)marker);
    assert(js_native_symbol_lookup("openal","font_audio_marker",&p)==JS_OK&&p==(uintptr_t)marker);
    assert(js_native_symbol_lookup("shaderc","shader_marker",&p)==JS_OK&&p==(uintptr_t)marker);
    assert(js_native_symbol_lookup(NULL,"utility_marker",&p)==JS_OK&&p==(uintptr_t)marker);
    assert(js_native_symbol_lookup(NULL,"font_audio_marker",&p)==JS_OK&&p==(uintptr_t)marker);
    assert(js_native_symbol_lookup(NULL,"shader_marker",&p)==JS_OK&&p==(uintptr_t)marker);
    assert(js_native_symbol_lookup("lwjgl","shader_marker",&p)==JS_UNAVAILABLE&&p==0);
    assert(js_native_module_available("missing",&available)==JS_UNAVAILABLE&&!available);
    assert(js_native_symbol_lookup("java","jdk_add",&p)==JS_OK&&((int (*)(int,int))p)(20,22)==42);
    assert(js_native_symbol_lookup("SDL3","app_mul",&p)==JS_OK&&((int (*)(int,int))p)(6,7)==42);
    assert(js_native_symbol_lookup(NULL,"jdk_add",&p)==JS_OK&&((int (*)(int,int))p)(20,22)==42);
    assert(js_native_symbol_lookup(NULL,"app_mul",&p)==JS_OK&&((int (*)(int,int))p)(6,7)==42);
    assert(js_native_symbol_lookup("SDL3","jdk_add",&p)==JS_UNAVAILABLE&&p==0);
    assert(js_native_symbol_lookup("unknown","app_mul",&p)==JS_UNAVAILABLE&&p==0);
    assert(js_native_resolver_seal()==JS_OK);
    assert(sc_install_composite_resolver()==JS_INCOMPATIBLE);
    return 0;
}
