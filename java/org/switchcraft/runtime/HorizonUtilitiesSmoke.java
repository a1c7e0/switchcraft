package org.switchcraft.runtime;

import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.IntBuffer;
import java.util.zip.CRC32;
import java.util.zip.DeflaterOutputStream;

import org.lwjgl.PointerBuffer;
import org.lwjgl.stb.STBImage;
import org.lwjgl.system.Library;
import org.lwjgl.system.MemoryStack;
import org.lwjgl.system.MemoryUtil;
import org.lwjgl.util.shaderc.Shaderc;
import org.lwjgl.util.spvc.Spvc;
import org.lwjgl.util.spvc.SpvcReflectedResource;
import org.lwjgl.util.spvc.Spv;

/** Real LWJGL STB, shaderc and SPIRV-Cross Java calls for the Horizon adapter. */
public final class HorizonUtilitiesSmoke {
    private static final byte[] PIXEL = { 0x10, (byte) 0x80, (byte) 0xE0, (byte) 0xFF };

    private HorizonUtilitiesSmoke() {}

    public static void main(String[] args) throws IOException {
        if (!NativeSymbols.moduleAvailable("shaderc")
                || !NativeSymbols.moduleAvailable("spirv-cross-c")) {
            throw new UnsatisfiedLinkError("Static shaderc/SPIRV-Cross providers are not linked");
        }
        Library.initialize();

        decodePngThroughStb();
        byte[] spirv = compileVertexShader();
        reflectStageInput(spirv);
        System.out.println("SWITCHCRAFT_UTILITIES_JAVA_PASS");
    }

    private static void decodePngThroughStb() throws IOException {
        byte[] png = createOnePixelPng();
        try (MemoryStack stack = MemoryStack.stackPush()) {
            IntBuffer width = stack.mallocInt(1);
            IntBuffer height = stack.mallocInt(1);
            IntBuffer sourceChannels = stack.mallocInt(1);
            ByteBuffer encoded = MemoryUtil.memAlloc(png.length);
            encoded.put(png).flip();
            try {
                ByteBuffer decoded = STBImage.stbi_load_from_memory(
                        encoded, width, height, sourceChannels, 4);
                if (decoded == null) {
                    throw new IllegalStateException("STB failed to decode generated PNG: "
                            + STBImage.stbi_failure_reason());
                }
                try {
                    if (width.get(0) != 1 || height.get(0) != 1 || sourceChannels.get(0) != 4) {
                        throw new AssertionError("Unexpected STB image dimensions/channel count");
                    }
                    for (int i = 0; i < PIXEL.length; i++) {
                        if (decoded.get(i) != PIXEL[i]) {
                            throw new AssertionError("STB PNG pixel mismatch at channel " + i);
                        }
                    }
                    System.out.println("SWITCHCRAFT_STB_PNG_JAVA_PASS width=1 height=1 rgba=10,80,e0,ff");
                } finally {
                    STBImage.stbi_image_free(decoded);
                }
            } finally {
                MemoryUtil.memFree(encoded);
            }
        }
    }

    private static byte[] createOnePixelPng() throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        output.write(new byte[] {(byte) 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A});

        ByteArrayOutputStream header = new ByteArrayOutputStream();
        try (DataOutputStream data = new DataOutputStream(header)) {
            data.writeInt(1);
            data.writeInt(1);
            data.writeByte(8); // bit depth
            data.writeByte(6); // RGBA
            data.writeByte(0); // compression
            data.writeByte(0); // filter
            data.writeByte(0); // interlace
        }
        writePngChunk(output, "IHDR", header.toByteArray());

        ByteArrayOutputStream compressed = new ByteArrayOutputStream();
        try (DeflaterOutputStream deflater = new DeflaterOutputStream(compressed)) {
            deflater.write(0); // PNG filter: None
            deflater.write(PIXEL);
        }
        writePngChunk(output, "IDAT", compressed.toByteArray());
        writePngChunk(output, "IEND", new byte[0]);
        return output.toByteArray();
    }

    private static void writePngChunk(ByteArrayOutputStream output, String type, byte[] data)
            throws IOException {
        byte[] name = type.getBytes(java.nio.charset.StandardCharsets.US_ASCII);
        try (DataOutputStream stream = new DataOutputStream(output)) {
            stream.writeInt(data.length);
            stream.write(name);
            stream.write(data);
            CRC32 crc = new CRC32();
            crc.update(name);
            crc.update(data);
            stream.writeInt((int) crc.getValue());
        }
    }

    private static byte[] compileVertexShader() {
        String source = "#version 450\n"
                + "layout(location = 0) in vec2 position;\n"
                + "void main() { gl_Position = vec4(position, 0.0, 1.0); }\n";
        long compiler = Shaderc.shaderc_compiler_initialize();
        if (compiler == 0) {
            throw new IllegalStateException("shaderc compiler initialization failed");
        }
        long result = 0;
        try {
            result = Shaderc.shaderc_compile_into_spv(compiler, source,
                    Shaderc.shaderc_glsl_vertex_shader, "utilities-smoke.vert", "main", 0);
            if (result == 0) {
                throw new IllegalStateException("shaderc returned a null result");
            }
            int status = Shaderc.shaderc_result_get_compilation_status(result);
            if (status != Shaderc.shaderc_compilation_status_success) {
                throw new IllegalStateException("shaderc compilation failed: "
                        + Shaderc.shaderc_result_get_error_message(result));
            }
            ByteBuffer output = Shaderc.shaderc_result_get_bytes(result);
            if (output == null || output.remaining() < 20 || output.getInt(output.position()) != 0x07230203) {
                throw new AssertionError("shaderc result is not a valid SPIR-V module");
            }
            byte[] words = new byte[output.remaining()];
            output.get(words);
            System.out.println("SWITCHCRAFT_SHADERC_JAVA_PASS bytes=" + words.length);
            return words;
        } finally {
            if (result != 0) Shaderc.shaderc_result_release(result);
            Shaderc.shaderc_compiler_release(compiler);
        }
    }

    private static void reflectStageInput(byte[] spirv) {
        try (MemoryStack stack = MemoryStack.stackPush()) {
            ByteBuffer bytes = MemoryUtil.memAlloc(spirv.length);
            bytes.put(spirv).flip();
            IntBuffer words = bytes.order(java.nio.ByteOrder.nativeOrder()).asIntBuffer();
            PointerBuffer contextOut = stack.mallocPointer(1);
            PointerBuffer irOut = stack.mallocPointer(1);
            PointerBuffer compilerOut = stack.mallocPointer(1);
            PointerBuffer resourcesOut = stack.mallocPointer(1);
            PointerBuffer listOut = stack.mallocPointer(1);
            PointerBuffer countOut = stack.mallocPointer(1);
            long context = 0;
            try {
                requireSpvc(Spvc.spvc_context_create(contextOut), "context create", 0);
                context = contextOut.get(0);
                requireSpvc(Spvc.spvc_context_parse_spirv(context, words, words.remaining(), irOut),
                        "SPIR-V parse", context);
                requireSpvc(Spvc.spvc_context_create_compiler(context, Spvc.SPVC_BACKEND_NONE,
                        irOut.get(0), Spvc.SPVC_CAPTURE_MODE_TAKE_OWNERSHIP, compilerOut),
                        "compiler create", context);
                long compiler = compilerOut.get(0);
                requireSpvc(Spvc.spvc_compiler_create_shader_resources(compiler, resourcesOut),
                        "shader resources", context);
                long resources = resourcesOut.get(0);
                requireSpvc(Spvc.spvc_resources_get_resource_list_for_type(resources,
                        Spvc.SPVC_RESOURCE_TYPE_STAGE_INPUT, listOut, countOut),
                        "stage-input reflection", context);
                long count = countOut.get(0);
                SpvcReflectedResource.Buffer inputs = SpvcReflectedResource.create(listOut.get(0), (int) count);
                boolean found = false;
                for (int i = 0; i < count; i++) {
                    SpvcReflectedResource input = inputs.get(i);
                    if ("position".equals(input.nameString())) {
                        int location = Spvc.spvc_compiler_get_decoration(
                                compiler, input.id(), Spv.SpvDecorationLocation);
                        if (location != 0) {
                            throw new AssertionError("SPIRV-Cross reported position at location " + location);
                        }
                        found = true;
                    }
                }
                if (!found) {
                    throw new AssertionError("SPIRV-Cross did not reflect stage input position");
                }
                System.out.println("SWITCHCRAFT_SPVC_REFLECTION_JAVA_PASS stage_input=position location=0");
            } finally {
                if (context != 0) Spvc.spvc_context_destroy(context);
                MemoryUtil.memFree(bytes);
            }
        }
    }

    private static void requireSpvc(int result, String operation, long context) {
        if (result != Spvc.SPVC_SUCCESS) {
            String detail = context == 0 ? "" : ": " + Spvc.spvc_context_get_last_error_string(context);
            throw new IllegalStateException("SPIRV-Cross " + operation + " failed (" + result + ")" + detail);
        }
    }
}
