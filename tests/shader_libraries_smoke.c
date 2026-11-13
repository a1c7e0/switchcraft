#include "switchcraft/shader_libraries.h"
#include <shaderc/shaderc.h>
#include <spirv_cross_c.h>

#include <stdint.h>
#include <stddef.h>
#include <string.h>

int main(void) {
    static const char source[] =
        "#version 450\n"
        "layout(location = 0) in vec3 position;\n"
        "void main() { gl_Position = vec4(position, 1.0); }\n";
    shaderc_compiler_t compiler = NULL;
    shaderc_compile_options_t options = NULL;
    shaderc_compilation_result_t result = NULL;
    spvc_context context = NULL;
    spvc_parsed_ir ir = NULL;
    spvc_compiler spvc = NULL;
    spvc_resources resources = NULL;
    const spvc_reflected_resource *inputs = NULL;
    size_t input_count = 0;
    const uint32_t *words;
    size_t word_count;
    int status = 1;

    if (!sc_shader_libraries_available("shaderc") ||
        !sc_shader_libraries_available("spirv-cross-c") ||
        sc_shader_libraries_available("shaderc.so") ||
        sc_shader_libraries_available(NULL) ||
        sc_shader_libraries_lookup("other", "shaderc_compiler_initialize") != 0 ||
        sc_shader_libraries_lookup("shaderc", "not_a_shaderc_function") != 0 ||
        sc_shader_libraries_lookup("shaderc", "shaderc_compiler_initialize") !=
            (uintptr_t)shaderc_compiler_initialize ||
        sc_shader_libraries_lookup("spirv-cross-c", "spvc_context_create") !=
            (uintptr_t)spvc_context_create) {
        return 10;
    }

    compiler = shaderc_compiler_initialize();
    options = shaderc_compile_options_initialize();
    if (compiler == NULL || options == NULL) goto cleanup;
    shaderc_compile_options_set_target_env(options, shaderc_target_env_vulkan,
                                           shaderc_env_version_vulkan_1_1);
    result = shaderc_compile_into_spv(compiler, source, sizeof(source) - 1,
                                      shaderc_vertex_shader, "shader-smoke.vert",
                                      "main", options);
    if (result == NULL || shaderc_result_get_compilation_status(result) !=
                          shaderc_compilation_status_success) goto cleanup;
    if (shaderc_result_get_length(result) < sizeof(uint32_t) ||
        shaderc_result_get_length(result) % sizeof(uint32_t) != 0) goto cleanup;
    words = (const uint32_t *)shaderc_result_get_bytes(result);
    word_count = shaderc_result_get_length(result) / sizeof(uint32_t);
    if (words == NULL || words[0] != 0x07230203u) goto cleanup;

    if (spvc_context_create(&context) != SPVC_SUCCESS || context == NULL) goto cleanup;
    if (spvc_context_parse_spirv(context, words, word_count, &ir) != SPVC_SUCCESS) goto cleanup;
    if (spvc_context_create_compiler(context, SPVC_BACKEND_NONE, ir,
                                     SPVC_CAPTURE_MODE_TAKE_OWNERSHIP, &spvc) != SPVC_SUCCESS) goto cleanup;
    if (spvc_compiler_create_shader_resources(spvc, &resources) != SPVC_SUCCESS) goto cleanup;
    if (spvc_resources_get_resource_list_for_type(resources, SPVC_RESOURCE_TYPE_STAGE_INPUT,
                                                   &inputs, &input_count) != SPVC_SUCCESS) goto cleanup;
    if (input_count != 1 || inputs == NULL || strcmp(inputs[0].name, "position") != 0) goto cleanup;
    status = 0;

cleanup:
    if (context != NULL) spvc_context_destroy(context);
    if (result != NULL) shaderc_result_release(result);
    if (options != NULL) shaderc_compile_options_release(options);
    if (compiler != NULL) shaderc_compiler_release(compiler);
    return status;
}
