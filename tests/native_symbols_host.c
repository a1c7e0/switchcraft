/* Host test provider only; production uses actual SDL3 and Vulkan addresses. */
#include <jni.h>
#include <javaswitch/native_resolver.h>
#include <switchcraft/native_symbols_jni.h>
#include <stdint.h>
#include <string.h>
static int host_sdl_version(void){return 3004016;}
static void host_vk_symbol(void){}
static int has_module(const char *m,void *c){(void)c;return m&&(!strcmp(m,"SDL3")||!strcmp(m,"vulkan"));}
static uintptr_t find_symbol(const char *m,const char *n,void *c){
    (void)c;
    if(!strcmp(m,"SDL3")&&!strcmp(n,"SDL_GetVersion"))return (uintptr_t)host_sdl_version;
    if(!strcmp(m,"vulkan")&&!strcmp(n,"vkGetInstanceProcAddr"))return (uintptr_t)host_vk_symbol;
    return 0;
}
JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM *vm,void *reserved){
    (void)reserved;JNIEnv *env=NULL;
    if((*vm)->GetEnv(vm,(void **)&env,JNI_VERSION_1_8)!=JNI_OK)return JNI_ERR;
    JsNativeResolver resolver={JS_NATIVE_RESOLVER_ABI_VERSION,sizeof(resolver),has_module,find_symbol,NULL};
    if(js_native_resolver_install(&resolver)!=JS_OK || sc_register_native_symbols(vm,env,NULL)!=0)return JNI_ERR;
    return JNI_VERSION_1_8;
}
