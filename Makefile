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
LAUNCHER_SOURCES := src/launcher.cpp src/launcher_console.cpp src/instances.cpp src/prism_metadata.cpp src/launcher_ui.cpp src/ui_canvas.cpp src/launcher_controller.cpp src/launcher_jobs.cpp src/launcher_session.cpp src/install.cpp src/download.cpp
LAUNCHER_HEADERS := src/instances.hpp src/prism_metadata.hpp src/launcher_ui.hpp src/ui_canvas.hpp src/launcher_controller.hpp src/launcher_jobs.hpp src/launcher_session.hpp src/install.hpp src/download.hpp
build/minecraft-launcher.elf: $(LAUNCHER_SOURCES) $(LAUNCHER_HEADERS) vendor/stb_truetype.h build/metadata.o build/platform.o build/java-runtime.stamp
	$(DK)g++ $(CXXFLAGS) -I$(PORT)/include -DCURL_STATICLIB -I$(JAVASDK)/include $(LDFLAGS) $(LAUNCHER_SOURCES) build/metadata.o build/platform.o $(JAVASDK)/lib/libjavaswitch.a -Wl,--start-group -lcurl -lz -lnx -lm -Wl,--end-group -o $@ -Wl,-Map,$@.map
build/switchcraft-install: tools/install.cpp src/install.cpp src/download.cpp src/prism_metadata.cpp src/metadata.cpp src/install.hpp src/download.hpp src/prism_metadata.hpp src/metadata.hpp | build
	g++ -std=c++17 -O2 -Wall -Wextra -Ivendor -Isrc tools/install.cpp src/install.cpp src/download.cpp src/prism_metadata.cpp src/metadata.cpp -lcurl -lcrypto -pthread -o $@
build/launcher-preview: tools/launcher-preview.cpp src/launcher_ui.cpp src/ui_canvas.cpp src/launcher_ui.hpp src/ui_canvas.hpp src/instances.hpp vendor/stb_truetype.h | build
	g++ -std=c++17 -O2 -Wall -Wextra -Ivendor -Isrc tools/launcher-preview.cpp src/launcher_ui.cpp src/ui_canvas.cpp -o $@
build/java-runtime.stamp: dependencies.lock.json scripts/build-java-runtime.sh scripts/prepare-java25-runtime.py | build dist
	JAVA_SWITCH_SOURCE=$(JAVA_SWITCH_SOURCE) bash scripts/build-java-runtime.sh > build/java-runtime.log 2>&1
build/switchcraft-launcher-bridge.jar: scripts/build-launcher-bridge.py java/org/switchcraft/launcher/VulkanOnlyAgent.java java/org/switchcraft/launcher/VulkanOnlyTransform.java build/java-runtime.stamp
	python3 scripts/build-launcher-bridge.py
build/switchcraft-lwjgl-horizon.jar: scripts/build-lwjgl-horizon.py vendor/lwjgl-horizon/org/lwjgl/system/Platform.java vendor/lwjgl-horizon/org/lwjgl/system/Library.java licenses/LWJGL-BSD-3-Clause.txt dependencies.lock.json build/java-runtime.stamp | build
	python3 scripts/build-lwjgl-horizon.py
build/switchcraft-native-smoke.jar: scripts/build-native-smoke.py java/org/switchcraft/runtime/NativeSymbols.java java/org/switchcraft/runtime/HorizonResolverSmoke.java build/java-runtime.stamp | build
	python3 scripts/build-native-smoke.py
dist/java-test.nro dist/ffi-test.nro dist/zero-services-test.nro dist/java25-test.nro: build/java-runtime.stamp
	cp $(JAVA_SWITCH_SOURCE)/dist/$(notdir $@) $@
build/composite_resolver.o: src/composite_resolver.c include/switchcraft/composite_resolver.h build/java-runtime.stamp
	$(DK)gcc $(CFLAGS) -mno-outline-atomics -I$(JAVASDK)/include -c $< -o $@
build/libswitchcraft-java-resolver.a: build/composite_resolver.o build/native_symbols_jni.o
	$(DK)ar rcs $@ $^
build/jdk_native_resolver.o: build/java-runtime.stamp
	$(DK)gcc $(CFLAGS) -mno-outline-atomics -I$(JAVASDK)/include -c $(JAVA25)/native/native_resolver.c -o $@
build/java25_integration.o: src/java25_integration.c src/platform.h include/switchcraft/composite_resolver.h build/java-runtime.stamp
	$(DK)gcc $(CFLAGS) -mno-outline-atomics -I$(JAVASDK)/include -c $< -o $@
build/native_symbols_jni.o: src/native_symbols_jni.c include/switchcraft/native_symbols_jni.h build/java-runtime.stamp
	$(DK)gcc $(CFLAGS) -mno-outline-atomics -I$(JAVASDK)/include -I$(JAVA25)/include -I$(JAVA25)/include/horizon -c $< -o $@
build/switchcraft-java25.elf: build/java25_integration.o build/libswitchcraft-java-resolver.a build/jdk_native_resolver.o build/platform.o build/libswitchcraft-native.a
	$(DK)g++ $(LDFLAGS) -mno-outline-atomics -Wl,-u,JNI_CreateJavaVM $^ .deps/sdl3/lib/libSDL3.a .deps/nvk/lib/libvulkan.a -Wl,--start-group $(JAVA25)/native/libjava.a $(JAVA25)/native/libzip.a $(JAVA25)/native/libjimage.a $(JAVA25)/native/libverify.a $(JAVA25)/native/libnet.a $(JAVA25)/native/libnio.a $(JAVA25)/native/libfallbackLinker.a $(JAVA25)/native/libsyslookup.a $(JAVA25)/native/libjli_manifest.a $(JAVA25)/native/libinstrument.a $(JAVA25)/native/libjvm.a $(JAVASDK)/lib/libjavaswitch.a -ldrm_nouveau -lzstd -lz -lnx -lc -lm -Wl,--end-group -o $@ -Wl,-Map,$@.map
build/sdl3.stamp: dependencies.lock.json patches/sdl3-vulkan-only.patch scripts/build-sdl3.py | build
	python3 scripts/build-sdl3.py > build/sdl3-build.log 2>&1
build/vulkan_present.o: src/vulkan_present.c build/sdl3.stamp | build
	$(DK)gcc $(CFLAGS) -I.deps/sdl3/include -I.deps/nvk/include -DVK_NO_PROTOTYPES -c $< -o $@
build/native_lookup.o: src/native_lookup.c include/switchcraft/native_lookup.h | build
	$(DK)gcc $(CFLAGS) -c $< -o $@
build/native_symbols_horizon.o: src/native_symbols_horizon.c include/switchcraft/native_lookup.h build/sdl3.stamp | build
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
