#ifndef SWITCHCRAFT_SHADER_LIBRARIES_H
#define SWITCHCRAFT_SHADER_LIBRARIES_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Native LWJGL shader library provider backed by upstream shaderc and
 * SPIRV-Cross C APIs.  Availability means the corresponding static archive
 * was built for this target; it does not promise a particular API entry. */
int sc_shader_libraries_available(const char *module);
uintptr_t sc_shader_libraries_lookup(const char *module, const char *name);

#ifdef __cplusplus
}
#endif

#endif
