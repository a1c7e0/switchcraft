#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export DEVKITPRO="${DEVKITPRO:-$PWD/.toolchain/opt/devkitpro}"
if [[ ! -x "$DEVKITPRO/devkitA64/bin/aarch64-none-elf-gcc" || ! -x "$DEVKITPRO/tools/bin/elf2nro" || ! -f "$DEVKITPRO/libnx/lib/libnx.a" ]]; then
    python3 scripts/bootstrap-toolchain.py
fi
python3 scripts/bootstrap-deps.py
mkdir -p build
make -j2 all 2>&1 | tee build/cross-build.log
python3 scripts/verify-native-link.py | tee build/native-link.log
make host-test 2>&1 | tee build/host-tests.log
python3 scripts/verify-artifacts.py | tee build/verification.json
scripts/package.sh
scripts/verify-artifacts.sh
