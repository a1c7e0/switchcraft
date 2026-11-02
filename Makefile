DEVKITPRO ?= $(CURDIR)/.toolchain/opt/devkitpro
export DEVKITPRO
DK := $(DEVKITPRO)/devkitA64/bin/aarch64-none-elf-
PORT := $(DEVKITPRO)/portlibs/switch
ARCH := -march=armv8-a+crc+crypto -mtune=cortex-a57 -mtp=soft -fPIE
CFLAGS := $(ARCH) -O2 -g -Wall -Wextra -ffunction-sections -fdata-sections -D__SWITCH__ -I$(DEVKITPRO)/libnx/include -Isrc
CXXFLAGS := $(CFLAGS) -std=c++17 -Ivendor
LDFLAGS := $(ARCH) -specs=$(DEVKITPRO)/libnx/switch.specs -L$(DEVKITPRO)/libnx/lib -L$(PORT)/lib -Wl,--gc-sections
TOOLS := $(DEVKITPRO)/tools/bin
APPS := switch-diagnostics

.PHONY: all clean host-test
all: $(APPS:%=dist/%.nro)
build dist:
	mkdir -p $@
build/platform.o: src/platform.c src/platform.h | build
	$(DK)gcc $(CFLAGS) -c $< -o $@
build/switch-diagnostics.elf: src/diagnostics.c build/platform.o
	$(DK)gcc $(CFLAGS) $(LDFLAGS) $^ -lnx -o $@ -Wl,-Map,$@.map
dist/%.nro: build/%.elf | dist
	$(TOOLS)/nacptool --create "$*" Switchcraft 0.1.0 build/$*.nacp
	$(TOOLS)/elf2nro $< $@ --nacp=build/$*.nacp --icon=$(DEVKITPRO)/libnx/default_icon.jpg
clean:
	rm -rf build dist
