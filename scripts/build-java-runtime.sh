#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
java_switch_source="${JAVA_SWITCH_SOURCE:-$PWD/.deps/java-switch}"
export DEVKITPRO="${DEVKITPRO:-$PWD/.toolchain/opt/devkitpro}"
python3 "$java_switch_source/scripts/bootstrap-deps.py"
if [[ ! -f "$java_switch_source/dist/openjdk25-horizon-runtime.tar.gz" || ! -f "$java_switch_source/dist/manifest.json" ]]; then
    # Clean-build workaround tracked at java-switch issue #1; no source edits.
    mkdir -p "$java_switch_source/build/openjdk25-horizon"
    (cd "$java_switch_source" && bash scripts/build-openjdk25-runtime.sh --with-instrument)
fi
python3 scripts/prepare-java25-runtime.py
for app in java-test ffi-test zero-services-test java25-test; do
    case "$app" in
      zero-services-test) elf="$java_switch_source/build/openjdk25-horizon/components/$app.elf" ;;
      java25-test) elf="$java_switch_source/build/openjdk25-horizon/runtime-link/$app.elf" ;;
      *) elf="$java_switch_source/build/$app.elf" ;;
    esac
    cp "$elf" "build/$app.elf"
    cp "$java_switch_source/dist/$app.nro" "dist/$app.nro"
done
git -C "$java_switch_source" rev-parse HEAD > build/java-runtime.stamp
