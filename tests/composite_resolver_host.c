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
static int jdk_module(const char *m,void *ctx){(void)ctx;return !m || !strcmp(m,"java") || (getenv("SC_TEST_COLLISION") && !strcmp(m,"SDL3"));}
static uintptr_t jdk_lookup(const char *m,const char *n,void *ctx){(void)ctx;return (!m||!strcmp(m,"java"))&&!strcmp(n,"jdk_add")?(uintptr_t)jdk_add:0;}
const JsNativeResolver js_openjdk25_native_resolver={JS_NATIVE_RESOLVER_ABI_VERSION,sizeof(JsNativeResolver),jdk_module,jdk_lookup,0};
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
        assert(js_native_module_available("SDL3",&available)==JS_UNAVAILABLE&&!available);
        return 0;
    }
    assert(sc_install_composite_resolver()==JS_OK);
    assert(js_native_module_available("java",&available)==JS_OK&&available);
    assert(js_native_module_available("SDL3",&available)==JS_OK&&available);
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
