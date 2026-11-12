#ifndef SWITCHCRAFT_LWJGL_CORE_H
#define SWITCHCRAFT_LWJGL_CORE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Static symbol provider for the supported, upstream LWJGL core JNI subset. */
int sc_lwjgl_core_available(const char *module);
uintptr_t sc_lwjgl_core_lookup(const char *module, const char *name);

#ifdef __cplusplus
}
#endif

#endif
