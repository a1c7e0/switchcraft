# Complete Switchcraft SD test package

Download **switchcraft-complete-test-suite-2026-11-08.zip** from
[the complete test-suite release](https://github.com/a1c7e0/switchcraft/releases/tag/test-suite-2026-11-08).
This is one ordinary ZIP, not split parts and not an overlay. No additional Java
or launcher package is needed. The release also provides SHA256SUMS and a manifest.

## Copy to the SD root

1. Extract the ZIP directly into the SD card root, merging its contents. The
   result must include `SD:/switch/java25-test/java25-test.nro` and
   `SD:/switch/minecraft-launcher/minecraft-launcher.nro`; do not copy a wrapper
   folder around these directories.
2. Keep the complete runtime images, diagnostic JARs, source archives and notices.
   NRO files alone are insufficient. This package does not supply personal
   launcher configuration, logs, Prism instances, worlds, game assets or accounts.
   Preserve existing user files when merging; packaged program/runtime files
   replace the earlier diagnostic versions.
3. Use Switch 1 with Atmosphere and **application-mode hbmenu** (your normal
   title-override setup). Album/applet mode is unsuitable for the VM baseline.
   No custom Java JAR, Minecraft installation or account is needed for the
   required native/Java diagnostics. Keep normal clocks.

The package contains nine applications: switch-diagnostics, java-test, ffi-test,
zero-services-test, vulkan-test, vulkan-present, java25-test, switchcraft-java25
and the graphical minecraft-launcher. It includes miniJVM's Java8 diagnostic
runtime, the complete genuine Java25 java.base/java.instrument image, Java25
Hello/JNI/FFM/startup-agent workloads and the composed SDL native smoke test.
The launcher includes online installation/repair and instance management.

## Run the tests

Start with [DEVICE_TEST_QUICKSTART.md](DEVICE_TEST_QUICKSTART.md):

1. Native prerequisites: SD/memory/threads, Java8 diagnostic, FFI and VM services.
2. Genuine Java25: standalone A (Hello), X (JNI/FFM), Y (startup agent), then
   combined A (Hello) and X (SDL JNI/FFM). **Start a fresh application process for
   every Java25 action.** Do not run multiple VM attempts inside one process.
3. Vulkan features, presentation/input and offscreen tests. These can be tested
   independently of Java. Run the deliberate SafeFetch fault probe last, after
   exporting ordinary logs.
4. Follow [LAUNCHER_TESTS.md](LAUNCHER_TESTS.md) for controller,
   touch, installation/repair, cancellation, profiles, import and archive/restore.

Full case IDs, expected markers and recovery instructions are in
[TEST_PLAN.md](TEST_PLAN.md). A successful download or native
graphics test does not establish Minecraft launch. Minecraft reaches its Demo
title on the separate Linux host reference; **Horizon VM startup, Java, JNI/FFM,
instrumentation, graphics and Minecraft execution remain NOT TESTED**. The
launcher cannot currently start Minecraft on Switch.

## Export logs

Most text logs append, so you can export after different ordinary tests. Export
before repeating the same case or trying a deliberate fault: snapshot-vulkan.json,
launcher-task-report.json and launch-plan.json hold only the most recent result.
If an application stalls, record the actual wait and HOME responsiveness, close
it, and preserve logs before retrying. Crash reports need separate manual review.

On a PC with Python3, run the included helper, substituting the mounted SD path
and a new output filename outside the SD card:

```sh
python3 /path/to/SD/switchcraft-docs/collect-feedback.py --sd-root /path/to/SD --output ./switchcraft-feedback-attempt-01.zip
```

The helper reads an explicit allowlist and does not modify the SD. It includes
the combined manifest and latest launcher task report, while excluding accounts,
game files and launch-plan.json. Copy any previous JSON report you need before
another attempt; review a launch plan separately before sharing it. Include
firmware/Atmosphere/hbmenu versions, application mode, button/action, wait time
and PASS/FAIL/NOT TESTED for each case.

## Provenance and reproduction

This combines native/runtime diagnostics from Switchcraft e08f36a, the launcher
from 13e9cff and java-switch b7c2ac7fd422bc2543e5c698db4e33a01cc0312d (SDK ABI1).
Per-binary source revisions are preserved in manifest.json. The three clearly
named source archives cover the base/runtime, launcher/curl/Prism integration
and current package tools. Licenses remain under switch/mc-runtime/licenses/.
No new VM/image build or physical execution is claimed by repackaging.

The root manifest records every payload file. To check the installed files from
the SD root on a PC with sha256sum:

```sh
sha256sum -c switchcraft-docs/SD_FILES_SHA256SUMS
```

From a clean source checkout, prepare the original base and launcher artifact
sets under dist/ and dist/launcher-foundation/. The exact immutable commits and
input hashes are in config/test-suite-inputs.json. Run:

```sh
python3 scripts/package-test-suite.py
```

The script verifies both complete input ZIP hashes/manifests, all nine NROs,
runtime image inventory, test/bridge JARs and the final ZIP members. It produces
dist/complete-test-suite/ with one ZIP, manifest.json and SHA256SUMS. It does not
require the runtime repository's original build archives or recompile any NRO.
