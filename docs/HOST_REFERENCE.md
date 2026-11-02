# Host-only snapshot 6 reference

**This is Linux reference evidence, not Switch execution or a remote execution
solution. The Horizon title-screen objective remains NOT ACHIEVED.**

Target/client: 26.4-snapshot-6, SHA-1
`8a97d5dafe80783525a2807b220527b65df724a5`. Exact official metadata is retained
under docs/evidence/official-metadata/. Its Java requirement is 25; the client
uses SDL3 and LWJGL 3.4.3/FFM, Vulkan, VMA, shaderc, SPIR-V Cross and FreeType.

Reference execution used Temurin 25.0.5+8 on Linux x86_64, Xvfb :97 (1280x720),
SDL3 X11 and Mesa 25.0.7 llvmpipe Vulkan 1.4.305 / LLVM 19.1.7. Official client,
libraries and assets were SHA-1 verified and kept only in /tmp or ignored cache.
Built-in Demo mode used an empty access token and no account credentials. The
client supplied its own default display name. Authentication code was not patched.

The first reference reached the accessibility screen and then Demo title. A
second run applied the strict Vulkan renderer transformation and reached the
same title screen. Screenshot and logs are retained:

* evidence/26.4-snapshot-6-HOST-ONLY-vulkan-strict-title.png
* evidence/26.4-snapshot-6-host-strict-vulkan.log
* evidence/snapshot6-host-result.json

The final checked-in reference script reproduced the strict title screen. Its
bridge JAR hash is recorded in snapshot6-host-result.json. The strict screenshot
and log above come from that final run. Selecting Quit Game stopped the client
normally; the log records `Stopping!`. A separate strict-run thread dump is
retained as evidence/26.4-snapshot-6-host-strict-threads.log.

The log records VULKAN_ONLY_APPLIED and `Using graphics backend Vulkan`, followed
by actual atlas creation and title rendering. A thread dump from the first run
shows vkQueuePresentKHR through VulkanGpuSurface.present and Minecraft.renderFrame.
No world was entered. Missing host audio disabled sound. Minecraft services/
Realms could not connect in this host environment; Demo title rendering continued.

The client retains an OpenGL fallback. `--graphicsBackend VULKAN` only prioritizes
Vulkan. Our original bridge replaces exactly getBackendsToTry with a one-element
VulkanBackend array, after checking the original class SHA-256. It changes no
authentication, device features or game content. Synthetic fixtures test that GL
is not instantiated and mismatched input hashes are rejected. The original game
class bytes are not redistributed. A custom child-loader experiment failed;
the tested implementation uses normal Java instrumentation and public Class-File
API, preserving the original game loader.

Reproduction on an ordinary Linux X11/Vulkan development machine:

```sh
bash scripts/build-all.sh
python3 tools/snapshot6-reference.py --download-assets
python3 tools/snapshot6-reference.py --run-demo
```

Use the normal system Vulkan ICD or set VK_DRIVER_FILES to a software ICD. The
reference script requires DISPLAY, uses the exact fixed metadata and explicit
VULKAN argument/bridge. It does not claim title success automatically; review
the captured screen/logs. The first-run Continue button may need to be selected.
The host environment used an Xvfb package and Mesa driver extracted without root;
those desktop binaries are not part of the SD package or Horizon architecture.
