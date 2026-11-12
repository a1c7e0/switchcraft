#include "switchcraft/lwjgl_utilities.h"

#include <stddef.h>
#include <string.h>

/* Generated from defined global function symbols in the compiled module objects. */
#include "lwjgl_utilities_exports.inc"

int sc_lwjgl_utilities_available(const char *module) {
    return module != NULL &&
           (strcmp(module, "lwjgl_stb") == 0 || strcmp(module, "lwjgl_vma") == 0);
}

uintptr_t sc_lwjgl_utilities_lookup(const char *module, const char *name) {
    size_t i;
    if ((module != NULL && !sc_lwjgl_utilities_available(module)) || name == NULL) return 0;
    for (i = 0; i < sizeof(sc_lwjgl_utilities_exports) / sizeof(sc_lwjgl_utilities_exports[0]); ++i) {
        const struct sc_lwjgl_utilities_export *entry = &sc_lwjgl_utilities_exports[i];
        if ((module == NULL || strcmp(module, entry->module) == 0) && strcmp(name, entry->name) == 0)
            return (uintptr_t)entry->address;
    }
    return 0;
}
