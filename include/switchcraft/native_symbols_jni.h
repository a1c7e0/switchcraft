#ifndef SWITCHCRAFT_NATIVE_SYMBOLS_JNI_H
#define SWITCHCRAFT_NATIVE_SYMBOLS_JNI_H
#ifdef __cplusplus
extern "C" {
#endif
/* JsVmReady callback; registers the runtime's static resolver bridge. */
int sc_register_native_symbols(void *vm,void *env,void *context);
#ifdef __cplusplus
}
#endif
#endif
