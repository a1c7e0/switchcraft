DEVKITPRO ?= $(CURDIR)/.toolchain/opt/devkitpro
export DEVKITPRO
DK := $(DEVKITPRO)/devkitA64/bin/aarch64-none-elf-
PORT := $(DEVKITPRO)/portlibs/switch
ARCH := -march=armv8-a+crc+crypto -mtune=cortex-a57 -mtp=soft -fPIE
CFLAGS := $(ARCH) -O2 -g -Wall -Wextra -ffunction-sections -fdata-sections -D__SWITCH__ -isystem $(DEVKITPRO)/libnx/include -Isrc
CXXFLAGS := $(CFLAGS) -std=c++17 -Ivendor
LDFLAGS := $(ARCH) -specs=$(DEVKITPRO)/libnx/switch.specs -L$(DEVKITPRO)/libnx/lib -L$(PORT)/lib -Wl,--gc-sections
TOOLS := $(DEVKITPRO)/tools/bin
APPS := switch-diagnostics opengl-test vulkan-test minecraft-launcher

.PHONY: all clean host-test
all: $(APPS:%=dist/%.nro)
build dist:
	mkdir -p $@
build/platform.o: src/platform.c src/platform.h | build
	$(DK)gcc $(CFLAGS) -c $< -o $@
build/switch-diagnostics.elf: src/diagnostics.c build/platform.o
	$(DK)gcc $(CFLAGS) $(LDFLAGS) $^ -lnx -o $@ -Wl,-Map,$@.map
build/opengl-test.elf: src/opengl.c build/platform.o
	$(DK)gcc $(CFLAGS) -I$(PORT)/include $(LDFLAGS) $^ -lglad -lEGL -lglapi -ldrm_nouveau -lstdc++ -lnx -lm -o $@ -Wl,-Map,$@.map
build/vulkan.o: src/vulkan.c | build
	$(DK)gcc $(CFLAGS) -I.deps/nvk/include -DVK_NO_PROTOTYPES -c $< -o $@
build/vulkan-test.elf: build/vulkan.o build/platform.o
	$(DK)g++ $(LDFLAGS) $^ .deps/nvk/lib/libvulkan.a -Wl,--start-group -ldrm_nouveau -lzstd -lz -lnx -lm -Wl,--end-group -o $@ -Wl,-Map,$@.map
build/metadata.o: src/metadata.cpp src/metadata.hpp vendor/json.hpp | build
	$(DK)g++ $(CXXFLAGS) -c $< -o $@
build/minecraft-launcher.elf: src/launcher.cpp build/metadata.o build/platform.o
	$(DK)g++ $(CXXFLAGS) $(LDFLAGS) $^ -lnx -o $@ -Wl,-Map,$@.map
build/switchcraft-inspect: src/metadata.cpp src/inspect.cpp src/metadata.hpp vendor/json.hpp | build
	g++ -std=c++17 -O2 -Wall -Wextra -Ivendor -Isrc src/metadata.cpp src/inspect.cpp -o $@
host-test: build/switchcraft-inspect
	python3 -m unittest discover -s tests -v
dist/%.nro: build/%.elf | dist
	$(TOOLS)/nacptool --create "$*" Switchcraft 0.1.0 build/$*.nacp
	$(TOOLS)/elf2nro $< $@ --nacp=build/$*.nacp --icon=$(DEVKITPRO)/libnx/default_icon.jpg
clean:
	rm -rf build dist
