#ifndef SWITCHCRAFT_LWJGL_UTILITIES_H
#define SWITCHCRAFT_LWJGL_UTILITIES_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Static providers for the pinned LWJGL STB and Vulkan Memory Allocator modules. */
int sc_lwjgl_utilities_available(const char *module);
uintptr_t sc_lwjgl_utilities_lookup(const char *module, const char *name);

#ifdef __cplusplus
}
#endif

#endif
