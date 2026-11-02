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
APPS := switch-diagnostics vulkan-test vulkan-present minecraft-launcher java-test ffi-test

.PHONY: all clean host-test FORCE
all: $(APPS:%=dist/%.nro) build/switchcraft-launcher-bridge.jar
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
build/minecraft-launcher.elf: src/launcher.cpp build/metadata.o build/platform.o build/java-runtime.stamp
	$(DK)g++ $(CXXFLAGS) -I$(JAVA_SWITCH_SOURCE)/include $(LDFLAGS) src/launcher.cpp build/metadata.o build/platform.o $(JAVA_SWITCH_SOURCE)/build/sdk/libjavaswitch.a -lnx -lm -o $@ -Wl,-Map,$@.map
build/java-runtime.stamp: dependencies.lock.json scripts/build-java-runtime.sh | build dist
	JAVA_SWITCH_SOURCE=$(JAVA_SWITCH_SOURCE) bash scripts/build-java-runtime.sh > build/java-runtime.log 2>&1
build/switchcraft-launcher-bridge.jar: scripts/build-launcher-bridge.py java/org/switchcraft/launcher/VulkanOnlyAgent.java java/org/switchcraft/launcher/VulkanOnlyTransform.java build/java-runtime.stamp
	python3 scripts/build-launcher-bridge.py
dist/java-test.nro dist/ffi-test.nro: build/java-runtime.stamp
	cp $(JAVA_SWITCH_SOURCE)/dist/$(notdir $@) $@
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
