# Java FreeType and OpenAL smoke check

`HorizonFontAudioSmoke` calls the pinned LWJGL 3.4.3 Java bindings for
FreeType and OpenAL. It uses `Library.loadNative` through the Switchcraft
Horizon `SharedLibrary` adapter and reaches the static procedures through
`NativeSymbols`; it does not call the C resolver directly from Java.

The FreeType check initializes the library, reads its version, and shuts it
down. When passed a font path, it also opens that face and renders the `A`
glyph. The OpenAL check creates an `ALC_SOFT_loopback` device and context,
submits synthetic PCM through the public AL buffer/source calls, renders
samples with `alcRenderSamplesSOFT`, and requires nonzero output. It does not
open or claim a physical audio device.

## Host Java integration test

Run `python3 tests/test_java_font_audio.py -v` after the Java 25 runtime SDK,
LWJGL core provider, Horizon compatibility JAR, and native host providers have
been built. The test compiles a temporary JNI fixture that installs the real
Java Switch resolver API, registers the genuine LWJGL core JNI exports, and
connects the host FreeType/OpenAL provider. It uses the public pinned core,
FreeType, and OpenAL JARs.

The fixture initializes the Linux host FFM linker first, then sets
`os.name=Horizon` to select the adapter. It leaves the host `os.arch` unchanged,
so it tests the actual x86 host FFM ABI rather than pretending to run AArch64
code. Set `JAVA_SWITCH_SOURCE` to the pinned Java Switch source checkout used
by the build; that tree supplies the generic resolver implementation for this
host fixture.

This test checks Java method signatures, module aliases, symbol lookup, JNI
registration, and real host library calls through the Horizon adapter. It is
not evidence of Java or audio execution on Switch hardware. The on-device
smoke class reports `hardware_output=NOT_TESTED`; a physical-device audio test
must record its result separately.
