#!/usr/bin/env python3
"""Verify the actual Horizon WSI executable exports the linked native proof."""
import os
from pathlib import Path
import re
import subprocess
ROOT=Path(__file__).resolve().parents[1]
dk=Path(os.environ.get('DEVKITPRO',ROOT/'.toolchain/opt/devkitpro'))
nm=dk/'devkitA64/bin/aarch64-none-elf-nm'
output=subprocess.check_output([str(nm),'--defined-only',str(ROOT/'build/vulkan-present.elf')],text=True)
symbols={line.split()[-1] for line in output.splitlines() if line.split()}
required={'sc_lookup_table','sc_horizon_native_lookup','SDL_CreateWindow','SDL_Vulkan_CreateSurface','vkGetInstanceProcAddr'}
missing=required-symbols
if missing: raise SystemExit('Missing native symbols: '+', '.join(sorted(missing)))
forbidden=sorted(name for name in symbols if re.match(r'^(egl[A-Z]|gl[A-Z])',name))
if forbidden: raise SystemExit('Unexpected GL/EGL API definitions: '+', '.join(forbidden))
print('AArch64 linked static symbol proof; GL/EGL API definitions absent: PASS')
combined=ROOT/'build/switchcraft-java25.elf'
output=subprocess.check_output([str(nm),'--defined-only',str(combined)],text=True)
linked={line.split()[-1] for line in output.splitlines() if line.split()}
required={'JNI_CreateJavaVM','JNI_OnLoad_java','Agent_OnLoad_instrument',
          'JNI_OnLoad_instrument','JLI_ManifestIterate','js_openjdk25_native_resolver',
          'sc_install_composite_resolver','SDL_CreateWindow','SDL_Vulkan_CreateSurface','vkGetInstanceProcAddr'}
if required-linked:raise SystemExit('Combined VM link missing: '+', '.join(sorted(required-linked)))
undefined=subprocess.check_output([str(nm),'-u',str(combined)],text=True).strip()
if undefined:raise SystemExit('Combined VM has unresolved symbols:\n'+undefined)
forbidden=sorted(name for name in linked if re.match(r'^(egl[A-Z]|gl[A-Z])',name))
if forbidden:raise SystemExit('Combined VM unexpectedly defines GL/EGL APIs: '+', '.join(forbidden))
print('Genuine VM, instrumentation, composed resolver and SDL/Vulkan link; zero undefined symbols: PASS')
