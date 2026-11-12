/* Public SDL functions present in the pinned Switch archive are generated into
 * the exact-name table. Vulkan global lookup exposes only gIPA; Vulkan device
 * functions continue through real instance/device dispatch. */
#define SDL_MAIN_HANDLED
#include <SDL3/SDL.h>
#include <SDL3/SDL_vulkan.h>
#include <vulkan/vulkan.h>
#include <switchcraft/native_lookup.h>
#include "sdl_symbols_generated.h"
extern PFN_vkVoidFunction vkGetInstanceProcAddr(VkInstance, const char *);
#define SDL_SYM(name) {"SDL3", #name, (ScNativeFunction)name},
static const ScNativeSymbol symbols[] = {
    SC_SDL_SYMBOLS(SDL_SYM)
    {"vulkan", "vkGetInstanceProcAddr", (ScNativeFunction)vkGetInstanceProcAddr}
};
ScNativeFunction sc_horizon_native_lookup(const char *module, const char *name) {
    return sc_lookup_table(symbols, sizeof(symbols)/sizeof(symbols[0]), module, name);
}
