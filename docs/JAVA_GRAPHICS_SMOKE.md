# Java SDL3 and Vulkan presentation smoke

`org.switchcraft.runtime.HorizonGraphicsSmoke` is a Java 25 workload built against public LWJGL 3.4.3 APIs. It initializes SDL3 video, opens a Vulkan window, loads SDL's Vulkan WSI support, creates a Vulkan instance using SDL's required surface extensions, selects a queue family that supports graphics and presentation, and creates a FIFO swapchain. It clears and presents 60 frames through Vulkan transfer commands.

The workload creates and destroys a genuine VMA allocator for its selected Vulkan instance, physical device, and logical device. VMA receives the upstream `VmaVulkanFunctions.set(instance, device)` dispatch table. The class performs no OpenGL setup, shader compilation, game asset loading, or game title verification.

## Horizon integration

Place the compiled class on the Java class path with these Java artifacts:

- `lwjgl_core.jar`
- `lwjgl-sdl-3.4.3.jar`
- `lwjgl-vulkan-3.4.3.jar`
- `lwjgl-vma-3.4.3.jar`

Switchcraft supplies Horizon-native implementations for SDL, Vulkan, and VMA. The workload uses no Linux native jars on Horizon. It is intended to run as one VM process on the existing worker strategy, with the C runner releasing the console before VM launch and restoring it after Java returns. It prints the SDL driver, selected Vulkan device and queue, surface extent and format, swapchain image count, and VMA lifecycle. `PRESENTATION_PASS frames=60` appears only after all 60 frames have been submitted and presented.

Map controller **B** to launch this class from the native diagnostic menu. The native runner owns console release and restore and result navigation; this Java class does not change controller ownership.

## Host validation

`tests/test_java_graphics_smoke.py` reads LWJGL artifact URLs and SHA-256 pins from `dependencies.lock.json`, downloads missing jars to `.deps/java-graphics`, verifies each digest, and compiles with the Java 25 host JDK. It does not need Minecraft's cache or version metadata. The ordinary test checks compilation and skips execution. To require and run the actual 60-frame host workload, set `SWITCHCRAFT_GRAPHICS_HOST_RUN=1` with a display and Vulkan ICD. A missing `DISPLAY`, Java failure, VMA failure, or missing `PRESENTATION_PASS frames=60` fails the test.

For example, with Xvfb and Debian Mesa llvmpipe extracted under `/tmp/r4-mc-reference/debian-mesa/root`:

```sh
DISPLAY=:93 SDL_VIDEODRIVER=x11 XDG_RUNTIME_DIR=/tmp \
VK_ICD_FILENAMES=/tmp/r4-mc-reference/debian-mesa/root/usr/share/vulkan/icd.d/lvp_icd.json \
LD_LIBRARY_PATH=/tmp/r4-mc-reference/debian-mesa/root/usr/lib/x86_64-linux-gnu \
SWITCHCRAFT_GRAPHICS_HOST_RUN=1 \
python3 -m unittest discover -s tests -p 'test_java_graphics_smoke.py' -v
```

An optional Khronos validation layer can be enabled through `VK_INSTANCE_LAYERS` and `VK_LAYER_PATH` if the host has that layer installed. This does not change the Horizon workload or its default behavior. On 2026-11-13, the smoke passed on Mesa llvmpipe 25.0.7 / LLVM 19.1.7 under Xvfb `:93`: SDL reported X11, the 960x540 surface had four swapchain images, VMA initialized and was destroyed, and all 60 frames completed. The same run with Debian 13's Vulkan validation layer 1.4.309.0 enabled emitted no validation errors. This is host-only evidence and does not establish a Horizon result.

## Resolved acquisition timeout

An earlier host run created a visible SDL window, a valid swapchain, and a VMA allocator, but `vkAcquireNextImageKHR` eventually timed out. Validation-layer output showed that `VkPresentInfoKHR.swapchainCount` was zero: LWJGL's `pSwapchains(...)` setter writes the pointer but does not fill this separate count field. The invalid present therefore released no acquired swapchain images, and later acquire calls exhausted the four-image swapchain. The workload now sets `swapchainCount(1)` explicitly. Validation also exposed that `VkSubmitInfo.pWaitSemaphores(...)` does not fill its separate `waitSemaphoreCount`; setting it to one ensures the acquire semaphore is consumed by the queue submission before it is reused. With both counts fixed, the validation-enabled run completed 60 frames without Vulkan validation errors.

The Vulkan loader fallback uses SDL's `vkGetInstanceProcAddr` address only for the exact `vkGetInstanceProcAddr` lookup and returns zero for other names. The regular Linux path already resolved the same loader address. Acquire retries remain bounded to ten seconds and service SDL events; failures report the exact Vulkan result and do not claim frame completion. No Horizon hardware result is implied.
