#include "switchcraft/font_audio.h"

#include <string.h>

/* Generated from defined global function symbols in the exact archives that
 * will be linked. This is a procedure table, not a fabricated library stub. */
#include "font_audio_exports.inc"

struct sc_font_audio_table {
    const char *module;
    const struct sc_font_audio_export *exports;
    size_t count;
};

static const struct sc_font_audio_table tables[] = {
    {"freetype", sc_freetype_exports,
     sizeof(sc_freetype_exports) / sizeof(sc_freetype_exports[0])},
    {"openal", sc_openal_exports,
     sizeof(sc_openal_exports) / sizeof(sc_openal_exports[0])},
};

static const struct sc_font_audio_table *find_table(const char *module) {
    size_t i;
    if (module == NULL) return NULL;
    for (i = 0; i < sizeof(tables) / sizeof(tables[0]); ++i)
        if (strcmp(module, tables[i].module) == 0) return &tables[i];
    return NULL;
}

int sc_font_audio_available(const char *module) {
    return find_table(module) != NULL;
}

uintptr_t sc_font_audio_lookup(const char *module, const char *name) {
    const struct sc_font_audio_table *table = find_table(module);
    size_t i;
    if (table == NULL || name == NULL) return 0;
    for (i = 0; i < table->count; ++i)
        if (strcmp(name, table->exports[i].name) == 0)
            return (uintptr_t)table->exports[i].address;
    return 0;
}

size_t sc_font_audio_export_count(const char *module) {
    const struct sc_font_audio_table *table = find_table(module);
    return table == NULL ? 0 : table->count;
}

const char *sc_font_audio_export_name(const char *module, size_t index) {
    const struct sc_font_audio_table *table = find_table(module);
    if (table == NULL || index >= table->count) return NULL;
    return table->exports[index].name;
}
