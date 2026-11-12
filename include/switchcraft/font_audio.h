#ifndef SWITCHCRAFT_FONT_AUDIO_H
#define SWITCHCRAFT_FONT_AUDIO_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Static FreeType/OpenAL Soft API providers, backed by genuine functions from
 * the selected target archives. Module names are exactly "freetype" and
 * "openal". Availability means the symbols are linked; it does not mean that
 * an audio device is present or initialized. */
int sc_font_audio_available(const char *module);
uintptr_t sc_font_audio_lookup(const char *module, const char *name);
size_t sc_font_audio_export_count(const char *module);
const char *sc_font_audio_export_name(const char *module, size_t index);

#ifdef __cplusplus
}
#endif

#endif
