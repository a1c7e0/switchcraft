#include "switchcraft/shader_libraries.h"

#include <stddef.h>
#include <string.h>

/* Generated from the compiled upstream archives.  Only defined text/weak
 * functions enter the tables, never declarations or exported data objects. */
#include "shader_libraries_exports.inc"

int sc_shader_libraries_available(const char *module) {
    return module != NULL &&
        (strcmp(module, "shaderc") == 0 || strcmp(module, "spirv-cross-c") == 0);
}

uintptr_t sc_shader_libraries_lookup(const char *module, const char *name) {
    size_t i;
    const struct sc_shader_library_export *exports;
    size_t count;
    if (module == NULL || name == NULL) return 0;
    if (strcmp(module, "shaderc") == 0) {
        exports = sc_shaderc_exports;
        count = sizeof(sc_shaderc_exports) / sizeof(sc_shaderc_exports[0]);
    } else if (strcmp(module, "spirv-cross-c") == 0) {
        exports = sc_spvc_exports;
        count = sizeof(sc_spvc_exports) / sizeof(sc_spvc_exports[0]);
    } else {
        return 0;
    }
    for (i = 0; i < count; ++i) {
        if (strcmp(name, exports[i].name) == 0)
            return (uintptr_t)exports[i].address;
    }
    return 0;
}
