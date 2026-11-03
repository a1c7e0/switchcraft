/* Real JNI bridge into the installed static native resolver. */
#include <switchcraft/native_symbols_jni.h>
#include <javaswitch/native_resolver.h>
#include <jni.h>
#include <stdint.h>
static jboolean JNICALL available(JNIEnv *env,jclass klass,jstring module){
    (void)klass;if(!module)return JNI_FALSE;
    const char *m=(*env)->GetStringUTFChars(env,module,NULL);if(!m)return JNI_FALSE;
    int found=0;int status=js_native_module_available(m,&found);
    (*env)->ReleaseStringUTFChars(env,module,m);
    return status==JS_OK&&found ? JNI_TRUE : JNI_FALSE;
}
static jlong JNICALL lookup(JNIEnv *env,jclass klass,jstring module,jstring name){
    (void)klass;if(!module||!name)return 0;
    const char *m=(*env)->GetStringUTFChars(env,module,NULL);if(!m)return 0;
    const char *n=(*env)->GetStringUTFChars(env,name,NULL);
    if(!n){(*env)->ReleaseStringUTFChars(env,module,m);return 0;}
    uintptr_t address=0;int status=js_native_symbol_lookup(m,n,&address);
    (*env)->ReleaseStringUTFChars(env,name,n);(*env)->ReleaseStringUTFChars(env,module,m);
    return status==JS_OK ? (jlong)address : 0;
}
int sc_register_native_symbols(void *vm,void *opaque_env,void *context){
    (void)vm;(void)context;JNIEnv *env=(JNIEnv *)opaque_env;
    if(!env)return -1;
    jclass klass=(*env)->FindClass(env,"org/switchcraft/runtime/NativeSymbols");
    if(!klass || (*env)->ExceptionCheck(env))return -1;
    JNINativeMethod methods[]={
        {"moduleAvailable","(Ljava/lang/String;)Z",(void *)available},
        {"lookup","(Ljava/lang/String;Ljava/lang/String;)J",(void *)lookup}
    };
    jint status=(*env)->RegisterNatives(env,klass,methods,2);
    (*env)->DeleteLocalRef(env,klass);
    return status==JNI_OK && !(*env)->ExceptionCheck(env) ? 0 : -1;
}
