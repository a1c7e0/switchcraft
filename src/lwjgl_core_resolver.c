#include "switchcraft/lwjgl_core.h"

#include <stddef.h>
#include <string.h>

/* Emitted by scripts/build-lwjgl-core.py from nm on the compiled upstream
 * objects. Keeping the inventory derived from object definitions prevents
 * resolver claims for declarations that did not make it into this build. */
#include "lwjgl_core_exports.inc"

int sc_lwjgl_core_available(const char *module) {
    return module != NULL && strcmp(module, "lwjgl") == 0;
}

uintptr_t sc_lwjgl_core_lookup(const char *module, const char *name) {
    size_t i;
    /* NULL is the Java resolver's global native scope. Named requests are
     * deliberately restricted to the one exact module owned by this provider. */
    if ((module != NULL && !sc_lwjgl_core_available(module)) || name == NULL) return 0;
    for (i = 0; i < sizeof(sc_lwjgl_core_exports) / sizeof(sc_lwjgl_core_exports[0]); ++i) {
        if (strcmp(name, sc_lwjgl_core_exports[i].name) == 0)
            return (uintptr_t)sc_lwjgl_core_exports[i].address;
    }
    return 0;
}
