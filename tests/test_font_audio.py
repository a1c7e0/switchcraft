#!/usr/bin/env python3
"""Exercise real host FreeType and OpenAL APIs through the static-provider map."""
from __future__ import annotations

import ctypes
import ctypes.util
import glob
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "build/font-audio/host/libswitchcraft-font-audio.so"


def _function(provider, module: bytes, name: bytes, restype, *argtypes):
    address = provider.sc_font_audio_lookup(module, name)
    if not address:
        raise AssertionError(f"missing {module.decode()} procedure {name.decode()}")
    return ctypes.CFUNCTYPE(restype, *argtypes)(address)


class FontAudioHostTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ctypes.util.find_library("freetype") or not ctypes.util.find_library("openal"):
            raise unittest.SkipTest("host FreeType/OpenAL runtime libraries are unavailable")
        subprocess.run(["python3", str(ROOT / "scripts/build-font-audio.py"), "--host"],
                       cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        cls.provider = ctypes.CDLL(str(LIBRARY))
        cls.provider.sc_font_audio_available.argtypes = [ctypes.c_char_p]
        cls.provider.sc_font_audio_available.restype = ctypes.c_int
        cls.provider.sc_font_audio_lookup.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        cls.provider.sc_font_audio_lookup.restype = ctypes.c_size_t
        cls.provider.sc_font_audio_export_count.argtypes = [ctypes.c_char_p]
        cls.provider.sc_font_audio_export_count.restype = ctypes.c_size_t
        cls.provider.sc_font_audio_export_name.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
        cls.provider.sc_font_audio_export_name.restype = ctypes.c_char_p

    def test_module_scope_and_export_inventory(self):
        provider = self.provider
        self.assertEqual(provider.sc_font_audio_available(None), 0)
        self.assertEqual(provider.sc_font_audio_export_count(b"unknown"), 0)
        self.assertEqual(provider.sc_font_audio_lookup(b"unknown", b"FT_Init_FreeType"), 0)
        for module, required in ((b"freetype", b"FT_Init_FreeType"),
                                 (b"openal", b"alcOpenDevice")):
            names = [provider.sc_font_audio_export_name(module, i)
                     for i in range(provider.sc_font_audio_export_count(module))]
            self.assertIn(required, names)
            self.assertIsNone(provider.sc_font_audio_export_name(module, len(names)))
        self.assertEqual(provider.sc_font_audio_lookup(None, b"alGetError"), 0)

    def test_real_freetype_renders_a_glyph(self):
        ft = self.provider
        self.assertEqual(ft.sc_font_audio_available(b"freetype"), 1)
        self.assertEqual(ft.sc_font_audio_available(b"unknown"), 0)
        self.assertGreater(ft.sc_font_audio_export_count(b"freetype"), 150)

        Library = ctypes.c_void_p
        Face = ctypes.c_void_p
        init = _function(ft, b"freetype", b"FT_Init_FreeType", ctypes.c_int,
                         ctypes.POINTER(Library))
        new_face = _function(ft, b"freetype", b"FT_New_Face", ctypes.c_int,
                             Library, ctypes.c_char_p, ctypes.c_long, ctypes.POINTER(Face))
        set_size = _function(ft, b"freetype", b"FT_Set_Pixel_Sizes", ctypes.c_int,
                             Face, ctypes.c_uint, ctypes.c_uint)
        load_char = _function(ft, b"freetype", b"FT_Load_Char", ctypes.c_int,
                              Face, ctypes.c_ulong, ctypes.c_int)
        done_face = _function(ft, b"freetype", b"FT_Done_Face", ctypes.c_int, Face)
        done = _function(ft, b"freetype", b"FT_Done_FreeType", ctypes.c_int, Library)

        fonts = (glob.glob("/usr/share/fonts/**/*.ttf", recursive=True)
                 + glob.glob("/usr/share/fonts/**/*.otf", recursive=True))
        self.assertTrue(fonts, "host test requires a redistributable system font")
        library, face = Library(), Face()
        self.assertEqual(init(ctypes.byref(library)), 0)
        try:
            self.assertEqual(new_face(library, fonts[0].encode(), 0, ctypes.byref(face)), 0)
            self.assertEqual(set_size(face, 0, 32), 0)
            self.assertEqual(load_char(face, ord("A"), 0), 0)
        finally:
            if face:
                done_face(face)
            done(library)

    def test_openal_procedures_and_real_loopback_when_available(self):
        al = self.provider
        self.assertEqual(al.sc_font_audio_available(b"openal"), 1)
        self.assertGreater(al.sc_font_audio_export_count(b"openal"), 150)
        get_proc = _function(al, b"openal", b"alcGetProcAddress", ctypes.c_void_p,
                             ctypes.c_void_p, ctypes.c_char_p)
        is_extension = _function(al, b"openal", b"alcIsExtensionPresent", ctypes.c_char,
                                 ctypes.c_void_p, ctypes.c_char_p)
        if not is_extension(None, b"ALC_SOFT_loopback"):
            self.skipTest("host OpenAL does not provide its software loopback output backend")

        def alc_proc(name: bytes, restype, *args):
            address = get_proc(None, name)
            if not address:
                self.skipTest(f"host OpenAL lacks {name.decode()}")
            return ctypes.CFUNCTYPE(restype, *args)(address)

        loopback_open = alc_proc(b"alcLoopbackOpenDeviceSOFT", ctypes.c_void_p, ctypes.c_char_p)
        render = alc_proc(b"alcRenderSamplesSOFT", None, ctypes.c_void_p,
                          ctypes.c_void_p, ctypes.c_int)
        channels = alc_proc(b"alcIsRenderFormatSupportedSOFT", ctypes.c_char,
                            ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int)
        create_context = _function(al, b"openal", b"alcCreateContext", ctypes.c_void_p,
                                   ctypes.c_void_p, ctypes.POINTER(ctypes.c_int))
        make_current = _function(al, b"openal", b"alcMakeContextCurrent", ctypes.c_char,
                                 ctypes.c_void_p)
        destroy_context = _function(al, b"openal", b"alcDestroyContext", None, ctypes.c_void_p)
        close_device = _function(al, b"openal", b"alcCloseDevice", ctypes.c_char, ctypes.c_void_p)
        device = loopback_open(None)
        if not device:
            self.skipTest("host OpenAL loopback device could not be opened")
        if not channels(device, 44100, 0x1501, 0x1402):
            close_device = _function(al, b"openal", b"alcCloseDevice", ctypes.c_char,
                                     ctypes.c_void_p)
            close_device(device)
            self.skipTest("host OpenAL loopback does not support stereo signed 16-bit output")
        attrs = (ctypes.c_int * 7)(0x1007, 44100, 0x1990, 0x1501, 0x1991, 0x1402, 0)
        context = create_context(device, attrs)
        self.assertTrue(context)
        try:
            self.assertTrue(make_current(context))
            gen_buffers = _function(al, b"openal", b"alGenBuffers", None,
                                    ctypes.c_int, ctypes.POINTER(ctypes.c_uint))
            buffer_data = _function(al, b"openal", b"alBufferData", None,
                                    ctypes.c_uint, ctypes.c_int, ctypes.c_void_p,
                                    ctypes.c_int, ctypes.c_int)
            gen_sources = _function(al, b"openal", b"alGenSources", None,
                                    ctypes.c_int, ctypes.POINTER(ctypes.c_uint))
            source_i = _function(al, b"openal", b"alSourcei", None,
                                 ctypes.c_uint, ctypes.c_int, ctypes.c_int)
            source_play = _function(al, b"openal", b"alSourcePlay", None, ctypes.c_uint)
            buffer, source = ctypes.c_uint(), ctypes.c_uint()
            gen_buffers(1, ctypes.byref(buffer))
            gen_sources(1, ctypes.byref(source))
            pcm = (ctypes.c_int16 * 4096)(*(int(12000 * ((i % 80) - 40) / 40)
                                               for i in range(4096)))
            buffer_data(buffer, 0x1101, pcm, ctypes.sizeof(pcm), 22050)
            source_i(source, 0x1009, buffer.value)
            source_play(source.value)
            output = (ctypes.c_int16 * 8192)()
            render(device, output, 4096)
            self.assertTrue(any(output), "OpenAL loopback produced only silence for synthetic PCM")
        finally:
            make_current(None)
            destroy_context(context)
            close_device(device)


if __name__ == "__main__":
    unittest.main()
