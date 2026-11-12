package org.switchcraft.runtime;

import java.nio.IntBuffer;

import org.lwjgl.PointerBuffer;
import org.lwjgl.openal.AL;
import org.lwjgl.openal.ALC;
import org.lwjgl.openal.ALCCapabilities;
import org.lwjgl.openal.ALCapabilities;
import org.lwjgl.openal.ALC10;
import org.lwjgl.openal.AL10;
import org.lwjgl.openal.SOFTLoopback;
import org.lwjgl.system.Library;
import org.lwjgl.system.MemoryStack;
import org.lwjgl.util.freetype.FT_Face;
import org.lwjgl.util.freetype.FreeType;

/** Java ABI/FFM smoke checks for the pinned LWJGL FreeType and OpenAL modules. */
public final class HorizonFontAudioSmoke {
    private HorizonFontAudioSmoke() {}

    public static void main(String[] args) {
        if (!NativeSymbols.moduleAvailable("freetype") || !NativeSymbols.moduleAvailable("openal")) {
            throw new UnsatisfiedLinkError("Static FreeType/OpenAL providers are not linked");
        }
        System.setProperty("org.lwjgl.openal.explicitInit", "true");
        Library.initialize();

        checkFreeType(args.length == 0 ? null : args[0]);
        checkOpenALLoopback();
        System.out.println("SWITCHCRAFT_FONT_AUDIO_JAVA_PASS hardware_output=NOT_TESTED");
    }

    private static void checkFreeType(String fontPath) {
        try (MemoryStack stack = MemoryStack.stackPush()) {
            PointerBuffer libraryBuffer = stack.mallocPointer(1);
            if (FreeType.FT_Init_FreeType(libraryBuffer) != FreeType.FT_Err_Ok) {
                throw new IllegalStateException("FT_Init_FreeType failed");
            }

            long library = libraryBuffer.get(0);
            try {
                IntBuffer major = stack.mallocInt(1);
                IntBuffer minor = stack.mallocInt(1);
                IntBuffer patch = stack.mallocInt(1);
                FreeType.FT_Library_Version(library, major, minor, patch);
                if (major.get(0) < 2) {
                    throw new AssertionError("Unexpected FreeType version: " + major.get(0));
                }

                if (fontPath != null && !fontPath.isBlank()) {
                    PointerBuffer faceBuffer = stack.mallocPointer(1);
                    int opened = FreeType.FT_New_Face(library, fontPath, 0, faceBuffer);
                    if (opened != FreeType.FT_Err_Ok) {
                        throw new IllegalStateException("FT_New_Face failed for supplied font: " + opened);
                    }
                    FT_Face face = FT_Face.create(faceBuffer.get(0));
                    try {
                        if (FreeType.FT_Set_Pixel_Sizes(face, 0, 32) != FreeType.FT_Err_Ok
                                || FreeType.FT_Get_Char_Index(face, 'A') == 0
                                || FreeType.FT_Load_Char(face, 'A', FreeType.FT_LOAD_RENDER) != FreeType.FT_Err_Ok) {
                            throw new IllegalStateException("FreeType could not render the A glyph");
                        }
                    } finally {
                        if (FreeType.FT_Done_Face(face) != FreeType.FT_Err_Ok) {
                            throw new IllegalStateException("FT_Done_Face failed");
                        }
                    }
                    System.out.println("SWITCHCRAFT_FREETYPE_GLYPH_PASS codepoint=65");
                }
                System.out.println("SWITCHCRAFT_FREETYPE_JAVA_PASS version=" + major.get(0) + "."
                        + minor.get(0) + "." + patch.get(0));
            } finally {
                if (FreeType.FT_Done_FreeType(library) != FreeType.FT_Err_Ok) {
                    throw new IllegalStateException("FT_Done_FreeType failed");
                }
            }
        }
    }

    private static void checkOpenALLoopback() {
        ALC.create("openal");
        long device = 0;
        long context = 0;
        int buffer = 0;
        int source = 0;
        try {
            ALCCapabilities router = ALC.getCapabilities();
            if (!router.ALC_SOFT_loopback) {
                throw new IllegalStateException("OpenAL does not expose ALC_SOFT_loopback");
            }
            device = SOFTLoopback.alcLoopbackOpenDeviceSOFT((String) null);
            if (device == 0) {
                throw new IllegalStateException("OpenAL loopback device could not be opened");
            }

            ALCCapabilities alc = ALC.createCapabilities(device);
            if (!alc.ALC_SOFT_loopback || !SOFTLoopback.alcIsRenderFormatSupportedSOFT(
                    device, 44100, SOFTLoopback.ALC_STEREO_SOFT, SOFTLoopback.ALC_SHORT_SOFT)) {
                throw new IllegalStateException("OpenAL loopback does not support stereo signed 16-bit PCM");
            }
            int[] attributes = {
                    ALC10.ALC_FREQUENCY, 44100,
                    SOFTLoopback.ALC_FORMAT_CHANNELS_SOFT, SOFTLoopback.ALC_STEREO_SOFT,
                    SOFTLoopback.ALC_FORMAT_TYPE_SOFT, SOFTLoopback.ALC_SHORT_SOFT,
                    0
            };
            context = ALC10.alcCreateContext(device, attributes);
            if (context == 0 || !ALC10.alcMakeContextCurrent(context)) {
                throw new IllegalStateException("OpenAL loopback context could not be made current");
            }
            ALCapabilities al = AL.createCapabilities(alc);
            if (al == null) {
                throw new IllegalStateException("OpenAL AL capabilities were not created");
            }

            buffer = AL10.alGenBuffers();
            source = AL10.alGenSources();
            short[] pcm = new short[4096];
            for (int i = 0; i < pcm.length; i++) {
                pcm[i] = (short) (12000.0 * Math.sin(2.0 * Math.PI * 440.0 * i / 22050.0));
            }
            AL10.alBufferData(buffer, AL10.AL_FORMAT_MONO16, pcm, 22050);
            AL10.alSourcei(source, AL10.AL_BUFFER, buffer);
            AL10.alSourcePlay(source);
            if (AL10.alGetError() != AL10.AL_NO_ERROR) {
                throw new IllegalStateException("OpenAL rejected synthetic PCM setup");
            }

            short[] rendered = new short[4096 * 2];
            SOFTLoopback.alcRenderSamplesSOFT(device, rendered, 4096);
            int nonzero = 0;
            for (short sample : rendered) {
                if (sample != 0) nonzero++;
            }
            if (nonzero == 0 || AL10.alGetError() != AL10.AL_NO_ERROR
                    || ALC10.alcGetError(device) != ALC10.ALC_NO_ERROR) {
                throw new IllegalStateException("OpenAL loopback produced no valid mixed PCM samples");
            }
            System.out.println("SWITCHCRAFT_OPENAL_LOOPBACK_JAVA_PASS frames=4096 nonzero=" + nonzero);
        } finally {
            if (source != 0) AL10.alDeleteSources(source);
            if (buffer != 0) AL10.alDeleteBuffers(buffer);
            if (context != 0) {
                ALC10.alcMakeContextCurrent(0);
                ALC10.alcDestroyContext(context);
            }
            if (device != 0) ALC10.alcCloseDevice(device);
            ALC.destroy();
        }
    }
}
