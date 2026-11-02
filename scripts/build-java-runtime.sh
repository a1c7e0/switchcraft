#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
java_switch_source="${JAVA_SWITCH_SOURCE:-$PWD/.deps/java-switch}"
export DEVKITPRO="${DEVKITPRO:-$PWD/.toolchain/opt/devkitpro}"
python3 "$java_switch_source/scripts/bootstrap-deps.py"
make -C "$java_switch_source" -j2 all
make -C "$java_switch_source" host-test
for app in java-test ffi-test; do
    cp "$java_switch_source/build/$app.elf" "build/$app.elf"
    cp "$java_switch_source/dist/$app.nro" "dist/$app.nro"
done
git -C "$java_switch_source" rev-parse HEAD > build/java-runtime.stamp
