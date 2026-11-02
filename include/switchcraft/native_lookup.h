#ifndef SWITCHCRAFT_NATIVE_LOOKUP_H
#define SWITCHCRAFT_NATIVE_LOOKUP_H
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Opaque function pointers: callers must use the exact C prototype and ABI. */
typedef void (*ScNativeFunction)(void);
typedef struct { const char *module; const char *name; ScNativeFunction function; } ScNativeSymbol;
ScNativeFunction sc_lookup_table(const ScNativeSymbol *symbols, size_t count,
                                 const char *module, const char *name);
/* Limited, statically linked proof of concept; not a Java native loader. */
ScNativeFunction sc_horizon_native_lookup(const char *module, const char *name);
#ifdef __cplusplus
}
#endif
#endif
