/* Limited static symbols already linked by the Vulkan presentation diagnostic.
 * No Java FFM/JNI loader integration or complete LWJGL bindings is implied. */
#define SDL_MAIN_HANDLED
#include <SDL3/SDL.h>
#include <SDL3/SDL_vulkan.h>
#include <vulkan/vulkan.h>
#include <switchcraft/native_lookup.h>
extern PFN_vkVoidFunction vkGetInstanceProcAddr(VkInstance, const char *);
#define SDL_SYM(name) {"SDL3", #name, (ScNativeFunction)name}
static const ScNativeSymbol symbols[] = {
    SDL_SYM(SDL_Init), SDL_SYM(SDL_Quit), SDL_SYM(SDL_GetError),
    SDL_SYM(SDL_CreateWindow), SDL_SYM(SDL_DestroyWindow),
    SDL_SYM(SDL_PollEvent), SDL_SYM(SDL_GetGamepads),
    SDL_SYM(SDL_OpenGamepad), SDL_SYM(SDL_CloseGamepad),
    SDL_SYM(SDL_Vulkan_GetInstanceExtensions), SDL_SYM(SDL_Vulkan_CreateSurface),
    {"vulkan", "vkGetInstanceProcAddr", (ScNativeFunction)vkGetInstanceProcAddr}
};
ScNativeFunction sc_horizon_native_lookup(const char *module, const char *name) {
    return sc_lookup_table(symbols, sizeof(symbols)/sizeof(symbols[0]), module, name);
}
