#pragma once

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define SC_MC_LAUNCH_CLASSPATH_CAP 65536
#define SC_MC_LAUNCH_STRING_CAP 1024
#define SC_MC_LAUNCH_MAX_ARGS 32
#define SC_MC_LAUNCH_MAX_OPTIONS 24

typedef struct ScMinecraftLaunchRequest {
    char classpath[SC_MC_LAUNCH_CLASSPATH_CAP];
    char main_class[128];
    char game_directory[SC_MC_LAUNCH_STRING_CAP];
    unsigned heap_mib;
    size_t argument_count;
    char arguments[SC_MC_LAUNCH_MAX_ARGS][SC_MC_LAUNCH_STRING_CAP];
    size_t option_count;
    char options[SC_MC_LAUNCH_MAX_OPTIONS][SC_MC_LAUNCH_STRING_CAP];
} ScMinecraftLaunchRequest;

typedef int (*ScMinecraftLaunchProgress)(void *context, unsigned long long bytes,
                                         unsigned long long total,
                                         const char *message);

/* Queue only a fixed official Demo request for a validated local profile. */
int sc_minecraft_launch_prepare(const char *runtime_root,
                                const char *shared_root,
                                const char *instance_id,
                                ScMinecraftLaunchProgress progress,
                                void *progress_context,
                                char *error, size_t error_capacity);
/* Consume the queue once, then rebuild all launch data from local metadata. */
int sc_minecraft_launch_consume(const char *runtime_root,
                                ScMinecraftLaunchRequest *request,
                                char *error, size_t error_capacity);
void sc_minecraft_launch_discard(const char *runtime_root);

#ifdef __cplusplus
}
#endif
