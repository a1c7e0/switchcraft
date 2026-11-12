# FreeType and OpenAL native providers

`freetype` and `openal` are genuine procedure maps backed by functions in the
selected native archives. They do not claim to implement either library.
`sc_font_audio_available` means that the named provider has linked procedures;
for OpenAL it does not mean that a Switch audio device was opened.

## Build and verification

Run `python3 scripts/build-font-audio.py --cross` after building SDL3 and the
other native dependencies. The script downloads and verifies OpenAL Soft 1.25.1
(`c41d64c6a35f6174bf4a27010aeac52a8d3bb2c6`, SHA-256
`5f8efe8dfba5e9307a50251ba615ace857c7fa9dddfe34130b83e213d7f7cf24`), builds
it as a static AArch64 Switch library, extracts public function exports from
the actual FreeType and OpenAL archives, and links a proof ELF with those
archives and their dependencies. Its link map must show the SDL3 audio device
functions and `pthread_create` backed by devkitPro `libsysbase` and libnx's
`__syscall_thread_create`; the empty `libpthread.a` must not be selected.
The generated symbols and provenance are recorded in
`build/font-audio/horizon/font-audio-build.json`.

The stock devkitPro OpenAL Soft archive is deliberately not used. It is built
with an SDL2 backend, whose SDL symbols cannot be linked safely into the SDL3
program. The pinned upstream rebuild enables SDL3 and disables SDL2 and other
platform backends. Its silent Null backend registration is removed, so a
missing SDL3 output device cannot appear as successful silent playback.
Switch SDL3's audio implementation calls libnx audren, but actual OpenAL device
initialization and audible playback still require device testing.

Run `python3 scripts/build-font-audio.py --host` and
`python3 tests/test_font_audio.py` for host API checks. The tests render a
system font glyph through FreeType and, where the host OpenAL Soft loopback
extension exists, render synthetic PCM through OpenAL into a memory buffer.
This checks the host libraries only; it does not test Switch hardware.

## Dependencies and licenses

The target FreeType archive is devkitPro `switch-freetype 2.13.3-1`; its static
link uses HarfBuzz, libpng, zlib and bzip2 from the pinned Switch portlibs.
OpenAL Soft is built from the pinned upstream archive above, with bundled fmt,
GSL and pffft. Package versions, archive hashes, backend selection and link
proof hashes are written to the build metadata. License notices for FreeType,
OpenAL Soft, fmt, GSL and pffft are under `licenses/font-audio/`.

OpenAL Soft is LGPL-2.0-or-later. A statically linked distribution must
preserve the corresponding source and provide the relinkable object files or
another compliant relinking mechanism. Keep the verified archive at
`.deps/openal-soft-1.25.1.tar.gz` and retain the matching generated provider,
OpenAL and dependent objects for any distributed binary. The source archive is
build input and does not belong in the minimal SD package. FreeType is offered
under its FreeType License; the bundled notice records the license choice.
