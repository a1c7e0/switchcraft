#include <switchcraft/native_lookup.h>
#include <string.h>
ScNativeFunction sc_lookup_table(const ScNativeSymbol *symbols, size_t count,
                                 const char *module, const char *name) {
    if (!symbols || !module || !name || !*module || !*name) return NULL;
    for (size_t i=0; i<count; ++i) {
        const ScNativeSymbol *s=&symbols[i];
        if (s->module && s->name && s->function && !strcmp(s->module,module) && !strcmp(s->name,name))
            return s->function;
    }
    return NULL;
}
