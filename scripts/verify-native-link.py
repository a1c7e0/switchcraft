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
