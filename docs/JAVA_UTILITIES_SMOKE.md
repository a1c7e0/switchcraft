# Java STB, Shaderc and SPIRV-Cross smoke

`org.switchcraft.runtime.HorizonUtilitiesSmoke` exercises the public LWJGL
3.4.3 Java APIs for three native utility modules. It decodes a generated
1-by-1 RGBA PNG through STB, compiles a GLSL vertex shader to SPIR-V through
Shaderc, and reflects the `position` stage input at location 0 through
SPIRV-Cross. Each operation checks its output before printing a pass marker.

On Horizon, Shaderc and SPIRV-Cross use the static `HorizonSharedLibrary`
adapter and the existing `NativeSymbols` resolver. STB retains LWJGL's JNI
path: `LibSTB` loads `lwjgl_stb`, and the linked STB JNI provider supplies the
native image implementation. The native smoke menu launches this class with
the existing L-button utility smoke selection. A final
`SWITCHCRAFT_UTILITIES_JAVA_PASS` is printed only after all three operations
complete.

## Linux host integration

Run `python3 tests/test_java_utilities.py -v`. The test fetches any missing
locked LWJGL JARs and builds missing host core, STB, Horizon compatibility,
Shaderc and SPIRV-Cross artifacts. It verifies the official locked JAR hashes,
compiles against the pinned APIs, and links a JNI fixture against the real host
archives. It loads the actual host `liblwjgl_stb.so` through
`java.library.path`. The fixture first initializes Linux's FFM linker, then
selects the Horizon adapter by setting `os.name=Horizon`; it leaves
`os.arch` untouched and reports the real host architecture. Thus the Java
calls exercise the adapter and real native implementations on Linux.

Passing host output includes:

```text
HOST_FFM_BOOTED os.arch=...
SWITCHCRAFT_STB_PNG_JAVA_PASS width=1 height=1 rgba=10,80,e0,ff
SWITCHCRAFT_SHADERC_JAVA_PASS bytes=...
SWITCHCRAFT_SPVC_REFLECTION_JAVA_PASS stage_input=position location=0
SWITCHCRAFT_UTILITIES_JAVA_PASS
```

These markers establish host Java/JNI/FFM integration through SDK ABI 1.
Execution on Horizon hardware remains untested.
