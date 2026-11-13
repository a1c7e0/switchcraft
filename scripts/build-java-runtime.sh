#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
java_switch_source="${JAVA_SWITCH_SOURCE:-$PWD/.deps/java-switch}"
export DEVKITPRO="${DEVKITPRO:-$PWD/.toolchain/opt/devkitpro}"
if [[ ! -f "$java_switch_source/dist/openjdk25-horizon-runtime.tar.gz" || ! -f "$java_switch_source/dist/manifest.json" ]]; then
    python3 "$java_switch_source/scripts/bootstrap-deps.py"
    runtime_profile=$(python3 -c 'import json; print(json.load(open("dependencies.lock.json"))["java_switch"].get("build_profile", "instrument"))')
    case "$runtime_profile" in
      instrument) runtime_build_options=(--with-instrument) ;;
      minecraft) runtime_build_options=(--with-instrument --with-minecraft) ;;
      *) printf 'Unknown Java runtime build profile: %s\n' "$runtime_profile" >&2; exit 1 ;;
    esac
    (cd "$java_switch_source" && bash scripts/build-openjdk25-runtime.sh "${runtime_build_options[@]}")
fi
python3 scripts/prepare-java25-runtime.py
runtime_link_directory=$(python3 -c 'import json; print("runtime-link-minecraft" if json.load(open("build/java25-integrated/runtime/openjdk25-horizon-runtime/runtime-package.json")).get("minecraft_profile") else "runtime-link")')
for app in java-test ffi-test zero-services-test java25-test; do
    case "$app" in
      zero-services-test) elf="$java_switch_source/build/openjdk25-horizon/components/$app.elf" ;;
      java25-test) elf="$java_switch_source/build/openjdk25-horizon/$runtime_link_directory/$app.elf" ;;
      *) elf="$java_switch_source/build/$app.elf" ;;
    esac
    cp "$elf" "build/$app.elf"
    if [[ -f "$elf.map" ]]; then
        cp "$elf.map" "build/$app.elf.map"
    else
        rm -f "build/$app.elf.map"
    fi
    cp "$java_switch_source/dist/$app.nro" "dist/$app.nro"
done
git -C "$java_switch_source" rev-parse HEAD > build/java-runtime.stamp
