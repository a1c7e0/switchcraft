DEVKITPRO ?= $(CURDIR)/.toolchain/opt/devkitpro
export DEVKITPRO
DK := $(DEVKITPRO)/devkitA64/bin/aarch64-none-elf-
PORT := $(DEVKITPRO)/portlibs/switch
ARCH := -march=armv8-a+crc+crypto -mtune=cortex-a57 -mtp=soft -fPIE
CFLAGS := $(ARCH) -O2 -g -Wall -Wextra -ffunction-sections -fdata-sections -D__SWITCH__ -isystem $(DEVKITPRO)/libnx/include -Isrc -Iinclude -Ibuild
CXXFLAGS := $(CFLAGS) -std=c++17 -Ivendor
LDFLAGS := $(ARCH) -specs=$(DEVKITPRO)/libnx/switch.specs -L$(DEVKITPRO)/libnx/lib -L$(PORT)/lib -Wl,--gc-sections
TOOLS := $(DEVKITPRO)/tools/bin
JAVA_SWITCH_SOURCE ?= $(CURDIR)/.deps/java-switch
APPS := switch-diagnostics vulkan-test vulkan-present minecraft-launcher java-test ffi-test zero-services-test java25-test switchcraft-java25
JAVA25 := build/java25-integrated/runtime/openjdk25-horizon-runtime
JAVASDK := build/java25-integrated/sdk

.PHONY: all clean host-test launcher-package FORCE
all: $(APPS:%=dist/%.nro) build/switchcraft-launcher-bridge.jar build/switchcraft-lwjgl-horizon.jar build/switchcraft-native-smoke.jar
launcher-package: dist/minecraft-launcher.nro
	python3 scripts/package-launcher.py
build dist:
	mkdir -p $@
build/build-info.h: FORCE scripts/build-info.py | build
	python3 scripts/build-info.py
build/platform.o: src/platform.c src/platform.h build/build-info.h | build
	$(DK)gcc $(CFLAGS) -c $< -o $@
build/switch-diagnostics.elf: src/diagnostics.c build/platform.o
	$(DK)gcc $(CFLAGS) $(LDFLAGS) $^ -lnx -o $@ -Wl,-Map,$@.map
build/vulkan.o: src/vulkan.c | build
	$(DK)gcc $(CFLAGS) -I.deps/nvk/include -DVK_NO_PROTOTYPES -c $< -o $@
build/vulkan-test.elf: build/vulkan.o build/platform.o
	$(DK)g++ $(LDFLAGS) $^ .deps/nvk/lib/libvulkan.a -Wl,--start-group -ldrm_nouveau -lzstd -lz -lnx -lm -Wl,--end-group -o $@ -Wl,-Map,$@.map
build/metadata.o: src/metadata.cpp src/metadata.hpp vendor/json.hpp | build
	$(DK)g++ $(CXXFLAGS) -c $< -o $@
LAUNCHER_SOURCES := src/launcher.cpp src/launcher_console.cpp src/instances.cpp src/prism_metadata.cpp src/launcher_ui.cpp src/ui_canvas.cpp src/launcher_controller.cpp src/launcher_jobs.cpp src/launcher_session.cpp src/install.cpp src/download.cpp src/minecraft_launch_request.cpp
LAUNCHER_HEADERS := src/instances.hpp src/prism_metadata.hpp src/launcher_ui.hpp src/ui_canvas.hpp src/launcher_controller.hpp src/launcher_jobs.hpp src/launcher_session.hpp src/install.hpp src/download.hpp include/switchcraft/minecraft_launch.h
LAUNCHER_OBJECTS := $(LAUNCHER_SOURCES:src/%.cpp=build/launcher/%.o)
build/launcher/%.o: src/%.cpp $(LAUNCHER_HEADERS) src/metadata.hpp vendor/stb_truetype.h build/java-runtime.stamp | build
	mkdir -p build/launcher
	$(DK)g++ $(CXXFLAGS) -I$(PORT)/include -DCURL_STATICLIB -I$(JAVASDK)/include -c $< -o $@
build/minecraft-launcher.elf: $(LAUNCHER_OBJECTS) build/metadata.o build/platform.o build/java-runtime.stamp
	$(DK)g++ $(LDFLAGS) $(LAUNCHER_OBJECTS) build/metadata.o build/platform.o $(JAVASDK)/lib/libjavaswitch.a -Wl,--start-group -lcurl -lz -lnx -lm -Wl,--end-group -o $@ -Wl,-Map,$@.map
build/switchcraft-install: tools/install.cpp src/install.cpp src/download.cpp src/prism_metadata.cpp src/metadata.cpp src/install.hpp src/download.hpp src/prism_metadata.hpp src/metadata.hpp | build
	g++ -std=c++17 -O2 -Wall -Wextra -Ivendor -Isrc tools/install.cpp src/install.cpp src/download.cpp src/prism_metadata.cpp src/metadata.cpp -lcurl -lcrypto -pthread -o $@
build/launcher-preview: tools/launcher-preview.cpp src/launcher_ui.cpp src/ui_canvas.cpp src/launcher_ui.hpp src/ui_canvas.hpp src/instances.hpp vendor/stb_truetype.h | build
	g++ -std=c++17 -O2 -Wall -Wextra -Ivendor -Isrc tools/launcher-preview.cpp src/launcher_ui.cpp src/ui_canvas.cpp -o $@
build/java-runtime.stamp: dependencies.lock.json scripts/build-java-runtime.sh scripts/prepare-java25-runtime.py | build dist
	JAVA_SWITCH_SOURCE=$(JAVA_SWITCH_SOURCE) bash scripts/build-java-runtime.sh > build/java-runtime.log 2>&1
build/switchcraft-launcher-bridge.jar: scripts/build-launcher-bridge.py java/org/switchcraft/launcher/VulkanOnlyAgent.java java/org/switchcraft/launcher/VulkanOnlyTransform.java build/java-runtime.stamp
	python3 scripts/build-launcher-bridge.py
LWJGL_OVERRIDE_SOURCES := $(wildcard vendor/lwjgl-horizon/org/lwjgl/system/*.java vendor/lwjgl-horizon/org/lwjgl/vulkan/*.java vendor/lwjgl-horizon/org/lwjgl/openal/*.java vendor/lwjgl-horizon/org/lwjgl/opengl/*.java)
build/switchcraft-lwjgl-horizon.jar: scripts/build-lwjgl-horizon.py $(LWJGL_OVERRIDE_SOURCES) licenses/LWJGL-BSD-3-Clause.txt dependencies.lock.json build/java-runtime.stamp | build
	python3 scripts/build-lwjgl-horizon.py
build/switchcraft-native-smoke.jar: scripts/build-native-smoke.py $(wildcard java/org/switchcraft/runtime/*.java) build/switchcraft-lwjgl-horizon.jar build/java-runtime.stamp | build
	python3 scripts/build-native-smoke.py
dist/java-test.nro dist/ffi-test.nro dist/zero-services-test.nro dist/java25-test.nro: build/java-runtime.stamp
	cp $(JAVA_SWITCH_SOURCE)/dist/$(notdir $@) $@
build/composite_resolver.o: src/composite_resolver.c include/switchcraft/composite_resolver.h include/switchcraft/lwjgl_core.h include/switchcraft/lwjgl_utilities.h include/switchcraft/font_audio.h include/switchcraft/shader_libraries.h build/java-runtime.stamp
	$(DK)gcc $(CFLAGS) -mno-outline-atomics -I$(JAVASDK)/include -c $< -o $@
build/libswitchcraft-java-resolver.a: build/composite_resolver.o build/native_symbols_jni.o
	$(DK)ar rcs $@ $^
build/lwjgl-core/horizon/liblwjgl-core.a: scripts/build-lwjgl-core.py patches/lwjgl-core-horizon.patch include/switchcraft/lwjgl_core.h src/lwjgl_core_resolver.c dependencies.lock.json build/java-runtime.stamp
	python3 scripts/build-lwjgl-core.py --cross > build/lwjgl-core.log 2>&1
build/lwjgl-utilities/horizon/liblwjgl-utilities.a: scripts/build-lwjgl-utilities.py include/switchcraft/lwjgl_utilities.h src/lwjgl_utilities_resolver.c dependencies.lock.json build/java-runtime.stamp build/lwjgl-core/horizon/liblwjgl-core.a
	python3 scripts/build-lwjgl-utilities.py --cross > build/lwjgl-utilities.log 2>&1
build/font-audio/horizon/libswitchcraft-font-audio.a: scripts/build-font-audio.py include/switchcraft/font_audio.h src/font_audio_resolver.c dependencies.lock.json build/sdl3.stamp
	python3 scripts/build-font-audio.py --cross > build/font-audio.log 2>&1
SHADER_BUILD := build/shader-libraries/horizon
SHADER_ARCHIVES = $(SHADER_BUILD)/shaderc/libshaderc/libshaderc_combined.a $(foreach module,c core glsl hlsl msl cpp reflect,$(SHADER_BUILD)/spirv-cross/libspirv-cross-$(module).a)
build/shader-libraries/horizon/libswitchcraft-shader-libraries-provider.a: scripts/build-shader-libraries.py patches/shader-libraries-horizon.patch src/shader_libraries_resolver.c include/switchcraft/shader_libraries.h dependencies.lock.json build/lwjgl-core/horizon/liblwjgl-core.a
	SWITCHCRAFT_SHADER_BUILD_DIR=$(CURDIR)/build/shader-libraries python3 scripts/build-shader-libraries.py --cross > build/shader-libraries.log 2>&1
MC_REQUEST_SOURCES := src/minecraft_launch_request.cpp src/instances.cpp src/install.cpp src/download.cpp src/prism_metadata.cpp
MC_REQUEST_OBJECTS := $(MC_REQUEST_SOURCES:src/%.cpp=build/launcher/%.o)
build/jdk_native_resolver.o: build/java-runtime.stamp
	$(DK)gcc $(CFLAGS) -mno-outline-atomics -I$(JAVASDK)/include -c $(JAVA25)/native/native_resolver.c -o $@
build/java25_integration.o: src/java25_integration.c src/platform.h include/switchcraft/composite_resolver.h include/switchcraft/minecraft_launch.h build/java-runtime.stamp
	$(DK)gcc $(CFLAGS) -mno-outline-atomics -I$(JAVASDK)/include -c $< -o $@
build/native_symbols_jni.o: src/native_symbols_jni.c include/switchcraft/native_symbols_jni.h build/java-runtime.stamp
	$(DK)gcc $(CFLAGS) -mno-outline-atomics -I$(JAVASDK)/include -I$(JAVA25)/include -I$(JAVA25)/include/horizon -c $< -o $@
JAVA25_NATIVE_ARCHIVES = $(sort $(wildcard $(JAVA25)/native/*.a))
build/switchcraft-java25.elf: build/java25_integration.o build/libswitchcraft-java-resolver.a build/jdk_native_resolver.o build/platform.o build/metadata.o $(MC_REQUEST_OBJECTS) build/libswitchcraft-native.a build/lwjgl-core/horizon/liblwjgl-core.a build/lwjgl-utilities/horizon/liblwjgl-utilities.a build/font-audio/horizon/libswitchcraft-font-audio.a build/shader-libraries/horizon/libswitchcraft-shader-libraries-provider.a
	$(DK)g++ $(LDFLAGS) -mno-outline-atomics -Wl,-u,JNI_CreateJavaVM $^ -Wl,--start-group .deps/sdl3/lib/libSDL3.a .deps/nvk/lib/libvulkan.a build/font-audio/openal-cross/libopenal.a $(SHADER_ARCHIVES) $(JAVA25_NATIVE_ARCHIVES) $(JAVASDK)/lib/libjavaswitch.a -lfreetype -lharfbuzz -lpng16 -lbz2 -lcurl -ldrm_nouveau -lzstd -lz -lnx -lc -lm -pthread -Wl,--end-group -o $@ -Wl,-Map,$@.map
build/sdl3.stamp: dependencies.lock.json patches/sdl3-vulkan-only.patch scripts/build-sdl3.py | build
	python3 scripts/build-sdl3.py > build/sdl3-build.log 2>&1
build/vulkan_present.o: src/vulkan_present.c build/sdl3.stamp | build
	$(DK)gcc $(CFLAGS) -I.deps/sdl3/include -I.deps/nvk/include -DVK_NO_PROTOTYPES -c $< -o $@
build/native_lookup.o: src/native_lookup.c include/switchcraft/native_lookup.h | build
	$(DK)gcc $(CFLAGS) -c $< -o $@
build/sdl_symbols_generated.h: scripts/generate-sdl-symbols.py build/sdl3.stamp | build
	python3 scripts/generate-sdl-symbols.py --cc $(DK)gcc --include .deps/sdl3/include --include .deps/nvk/include
build/native_symbols_horizon.o: src/native_symbols_horizon.c include/switchcraft/native_lookup.h build/sdl_symbols_generated.h build/sdl3.stamp | build
	$(DK)gcc $(CFLAGS) -I.deps/sdl3/include -I.deps/nvk/include -DVK_NO_PROTOTYPES -c $< -o $@
build/libswitchcraft-native.a: build/native_lookup.o build/native_symbols_horizon.o
	$(DK)ar rcs $@ $^
build/vulkan-present.elf: build/vulkan_present.o build/platform.o build/libswitchcraft-native.a
	$(DK)g++ $(LDFLAGS) $^ .deps/sdl3/lib/libSDL3.a .deps/nvk/lib/libvulkan.a -Wl,--start-group -ldrm_nouveau -lzstd -lz -lnx -lm -Wl,--end-group -o $@ -Wl,-Map,$@.map
build/switchcraft-inspect: src/metadata.cpp src/inspect.cpp src/metadata.hpp vendor/json.hpp | build
	g++ -std=c++17 -O2 -Wall -Wextra -Ivendor -Isrc src/metadata.cpp src/inspect.cpp -o $@
host-test: all build/switchcraft-inspect
	python3 -m unittest discover -s tests -v
dist/%.nro: build/%.elf | dist
	$(TOOLS)/nacptool --create "$*" Switchcraft 0.1.0 build/$*.nacp
	$(TOOLS)/elf2nro $< $@ --nacp=build/$*.nacp --icon=$(DEVKITPRO)/libnx/default_icon.jpg
clean:
	rm -rf build dist
