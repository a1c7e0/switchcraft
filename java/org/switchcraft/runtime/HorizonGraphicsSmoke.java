package org.switchcraft.runtime;

import org.lwjgl.PointerBuffer;
import org.lwjgl.sdl.SDL_Event;
import org.lwjgl.system.Configuration;
import org.lwjgl.system.FunctionProvider;
import org.lwjgl.system.MemoryStack;
import org.lwjgl.vulkan.*;
import org.lwjgl.util.vma.VmaAllocatorCreateInfo;
import org.lwjgl.util.vma.VmaVulkanFunctions;
import static org.lwjgl.util.vma.Vma.*;

import java.nio.IntBuffer;
import java.nio.LongBuffer;

import static org.lwjgl.sdl.SDLInit.SDL_INIT_VIDEO;
import static org.lwjgl.sdl.SDLInit.SDL_Init;
import static org.lwjgl.sdl.SDLInit.SDL_Quit;
import static org.lwjgl.sdl.SDLError.SDL_GetError;
import static org.lwjgl.sdl.SDLEvents.SDL_EVENT_QUIT;
import static org.lwjgl.sdl.SDLEvents.SDL_PollEvent;
import static org.lwjgl.sdl.SDLVideo.*;
import static org.lwjgl.sdl.SDLTimer.SDL_Delay;
import static org.lwjgl.sdl.SDLVulkan.*;
import static org.lwjgl.vulkan.KHRSurface.*;
import static org.lwjgl.vulkan.KHRSwapchain.*;
import static org.lwjgl.vulkan.VK10.*;

/** Real SDL3 + Vulkan swapchain clear/present workload; shared by Horizon and host smoke runners. */
public final class HorizonGraphicsSmoke {
    private static final int FRAME_LIMIT = 60;
    private static final long NULL = 0L;
    private static final long ACQUIRE_DEADLINE_NS = 10_000_000_000L;
    private static final long ACQUIRE_SLICE_NS = 100_000_000L;
    private HorizonGraphicsSmoke() {}

    private static void vk(int result, String stage) {
        if (result != VK_SUCCESS) throw new IllegalStateException(stage + " VkResult=" + result);
    }

    public static void main(String[] args) {
        Configuration.VULKAN_EXPLICIT_INIT.set(true);
        run(FRAME_LIMIT);
    }

    public static int run(int frameLimit) {
        Configuration.VULKAN_EXPLICIT_INIT.set(true);
        if (frameLimit < 1) throw new IllegalArgumentException("frameLimit must be positive");
        long window = NULL, surface = NULL, swapchain = NULL, commandPool = NULL, imageAvailable = NULL, fence = NULL, allocator = NULL;
        VkInstance instance = null;
        VkDevice device = null;
        VkQueue queue = null;
        long[] imageHandles = null, renderFinished = null;
        boolean sdlInitialized = false;
        Throwable primary = null;
        int completed = 0;
        try {
            if (!SDL_Init(SDL_INIT_VIDEO)) throw new IllegalStateException("SDL_Init failed: " + SDL_GetError());
            sdlInitialized = true;
            window = SDL_CreateWindow("Switchcraft Java Vulkan", 960, 540, SDL_WINDOW_VULKAN | SDL_WINDOW_RESIZABLE);
            if (window == NULL) throw new IllegalStateException("SDL_CreateWindow failed: " + SDL_GetError());
            if (!SDL_ShowWindow(window)) throw new IllegalStateException("SDL_ShowWindow failed: " + SDL_GetError());
            if (!SDL_SyncWindow(window)) throw new IllegalStateException("SDL_SyncWindow failed: " + SDL_GetError());
            long windowFlags = SDL_GetWindowFlags(window);
            if ((windowFlags & SDL_WINDOW_HIDDEN) != 0) throw new IllegalStateException("SDL window remained hidden after SDL_ShowWindow/SDL_SyncWindow");
            System.out.printf("SDL window synchronized: flags=0x%x hidden=false%n", windowFlags);
            System.out.println("SDL video driver: " + SDL_GetCurrentVideoDriver());
            if (!SDL_Vulkan_LoadLibrary((String)null)) throw new IllegalStateException("SDL_Vulkan_LoadLibrary failed: " + SDL_GetError());
            long sdlGetInstanceProcAddr = SDL_Vulkan_GetVkGetInstanceProcAddr();
            if (sdlGetInstanceProcAddr == NULL) throw new IllegalStateException("SDL returned a null vkGetInstanceProcAddr: " + SDL_GetError());
            // Resolve all Vulkan dispatch through SDL's loader so the instance and SDL-created surface
            // cannot be owned by separate Vulkan loader copies.
            VK.create();
            FunctionProvider lwjglVulkanProvider = VK.getFunctionProvider();
            long lwjglGetInstanceProcAddr = lwjglVulkanProvider.getFunctionAddress("vkGetInstanceProcAddr");
            System.out.printf("Vulkan loader gIPA: SDL=0x%x LWJGL=0x%x%n", sdlGetInstanceProcAddr, lwjglGetInstanceProcAddr);
            if (sdlGetInstanceProcAddr != lwjglGetInstanceProcAddr) {
                VK.destroy();
                VK.create((name) -> "vkGetInstanceProcAddr".equals(name) ? sdlGetInstanceProcAddr : NULL);
                System.out.println("LWJGL Vulkan global dispatch now uses SDL's loader");
            }

            try (MemoryStack stack = MemoryStack.stackPush()) {
                PointerBuffer extensions = SDL_Vulkan_GetInstanceExtensions();
                if (extensions == null || !extensions.hasRemaining()) throw new IllegalStateException("SDL returned no Vulkan surface extensions: " + SDL_GetError());
                VkApplicationInfo app = VkApplicationInfo.calloc(stack)
                    .sType(VK_STRUCTURE_TYPE_APPLICATION_INFO).pApplicationName(stack.UTF8("Switchcraft Java presentation smoke"))
                    .applicationVersion(1).pEngineName(stack.UTF8("Switchcraft" )).engineVersion(1).apiVersion(VK_API_VERSION_1_0);
                VkInstanceCreateInfo create = VkInstanceCreateInfo.calloc(stack)
                    .sType(VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO).pApplicationInfo(app).ppEnabledExtensionNames(extensions);
                PointerBuffer out = stack.mallocPointer(1);
                vk(vkCreateInstance(create, null, out), "vkCreateInstance");
                instance = new VkInstance(out.get(0), create);
                LongBuffer surfaceOut = stack.mallocLong(1);
                if (!SDL_Vulkan_CreateSurface(window, instance, null, surfaceOut)) throw new IllegalStateException("SDL_Vulkan_CreateSurface failed: " + SDL_GetError());
                surface = surfaceOut.get(0);

                IntBuffer count = stack.ints(0);
                vk(vkEnumeratePhysicalDevices(instance, count, null), "vkEnumeratePhysicalDevices(count)");
                if (count.get(0) == 0) throw new IllegalStateException("Vulkan reports no physical devices");
                PointerBuffer physicals = stack.mallocPointer(count.get(0));
                vk(vkEnumeratePhysicalDevices(instance, count, physicals), "vkEnumeratePhysicalDevices(list)");
                VkPhysicalDevice physical = null;
                int family = -1;
                for (int p = 0; p < count.get(0) && physical == null; p++) {
                    VkPhysicalDevice candidate = new VkPhysicalDevice(physicals.get(p), instance);
                    IntBuffer qcount = stack.ints(0);
                    vkGetPhysicalDeviceQueueFamilyProperties(candidate, qcount, null);
                    VkQueueFamilyProperties.Buffer props = VkQueueFamilyProperties.calloc(qcount.get(0), stack);
                    vkGetPhysicalDeviceQueueFamilyProperties(candidate, qcount, props);
                    for (int q = 0; q < qcount.get(0); q++) {
                        IntBuffer supported = stack.ints(VK_FALSE);
                        vk(vkGetPhysicalDeviceSurfaceSupportKHR(candidate, q, surface, supported), "vkGetPhysicalDeviceSurfaceSupportKHR");
                        if (props.get(q).queueCount() > 0 && (props.get(q).queueFlags() & VK_QUEUE_GRAPHICS_BIT) != 0 && supported.get(0) == VK_TRUE) {
                            physical = candidate; family = q; break;
                        }
                    }
                }
                if (physical == null) throw new IllegalStateException("No queue family supports both graphics and SDL surface presentation");
                VkPhysicalDeviceProperties gpu = VkPhysicalDeviceProperties.malloc(stack);
                vkGetPhysicalDeviceProperties(physical, gpu);
                System.out.println("Vulkan physical device: " + gpu.deviceNameString() + " api=" + VK_VERSION_MAJOR(gpu.apiVersion()) + "." + VK_VERSION_MINOR(gpu.apiVersion()) + " queue=" + family);

                java.nio.FloatBuffer priority = stack.floats(1.0f);
                VkDeviceQueueCreateInfo.Buffer qci = VkDeviceQueueCreateInfo.calloc(1, stack);
                qci.get(0).sType(VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO).queueFamilyIndex(family).pQueuePriorities(priority);
                PointerBuffer deviceExt = stack.pointers(stack.UTF8("VK_KHR_swapchain"));
                VkDeviceCreateInfo dci = VkDeviceCreateInfo.calloc(stack).sType(VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO)
                    .pQueueCreateInfos(qci).ppEnabledExtensionNames(deviceExt);
                PointerBuffer deviceOut = stack.mallocPointer(1);
                vk(vkCreateDevice(physical, dci, null, deviceOut), "vkCreateDevice");
                device = new VkDevice(deviceOut.get(0), physical, dci);
                VmaVulkanFunctions vmaFunctions = VmaVulkanFunctions.calloc(stack).set(instance, device);
                VmaAllocatorCreateInfo vmaInfo = VmaAllocatorCreateInfo.calloc(stack).physicalDevice(physical)
                    .device(device).instance(instance).vulkanApiVersion(VK_API_VERSION_1_0).pVulkanFunctions(vmaFunctions);
                PointerBuffer allocatorOut = stack.mallocPointer(1);
                vk(vmaCreateAllocator(vmaInfo, allocatorOut), "vmaCreateAllocator");
                allocator = allocatorOut.get(0);
                System.out.println("VMA allocator initialized with instance/device dispatch");
                PointerBuffer queueOut = stack.mallocPointer(1);
                vkGetDeviceQueue(device, family, 0, queueOut);
                queue = new VkQueue(queueOut.get(0), device);

                VkSurfaceCapabilitiesKHR caps = VkSurfaceCapabilitiesKHR.malloc(stack);
                vk(vkGetPhysicalDeviceSurfaceCapabilitiesKHR(physical, surface, caps), "vkGetPhysicalDeviceSurfaceCapabilitiesKHR");
                if ((caps.supportedUsageFlags() & VK_IMAGE_USAGE_TRANSFER_DST_BIT) == 0) throw new IllegalStateException("Surface does not support transfer-destination swapchain images");
                IntBuffer formatCount = stack.ints(0);
                vk(vkGetPhysicalDeviceSurfaceFormatsKHR(physical, surface, formatCount, null), "vkGetPhysicalDeviceSurfaceFormatsKHR(count)");
                if (formatCount.get(0) == 0) throw new IllegalStateException("Surface has no formats");
                VkSurfaceFormatKHR.Buffer formats = VkSurfaceFormatKHR.calloc(formatCount.get(0), stack);
                vk(vkGetPhysicalDeviceSurfaceFormatsKHR(physical, surface, formatCount, formats), "vkGetPhysicalDeviceSurfaceFormatsKHR(list)");
                VkSurfaceFormatKHR format = formats.get(0);
                for (int i = 0; i < formats.capacity(); i++) {
                    VkSurfaceFormatKHR f = formats.get(i);
                    if (f.format() == VK_FORMAT_B8G8R8A8_UNORM || f.format() == VK_FORMAT_R8G8B8A8_UNORM) { format = f; break; }
                }
                int width = caps.currentExtent().width(), height = caps.currentExtent().height();
                if (width == 0xFFFFFFFF) {
                    IntBuffer w = stack.ints(0), h = stack.ints(0);
                    SDL_GetWindowSizeInPixels(window, w, h);
                    width = Math.max(caps.minImageExtent().width(), Math.min(caps.maxImageExtent().width(), w.get(0)));
                    height = Math.max(caps.minImageExtent().height(), Math.min(caps.maxImageExtent().height(), h.get(0)));
                }
                int minImages = caps.minImageCount() + 1;
                if (caps.maxImageCount() > 0) minImages = Math.min(minImages, caps.maxImageCount());
                int alpha = Integer.lowestOneBit(caps.supportedCompositeAlpha());
                if (alpha == 0) throw new IllegalStateException("Surface has no supported composite alpha mode");
                final int swapWidth = width, swapHeight = height;
                VkSwapchainCreateInfoKHR sci = VkSwapchainCreateInfoKHR.calloc(stack).sType(VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR)
                    .surface(surface).minImageCount(minImages).imageFormat(format.format()).imageColorSpace(format.colorSpace())
                    .imageExtent(e -> e.width(swapWidth).height(swapHeight)).imageArrayLayers(1).imageUsage(VK_IMAGE_USAGE_TRANSFER_DST_BIT)
                    .imageSharingMode(VK_SHARING_MODE_EXCLUSIVE).preTransform(caps.currentTransform()).compositeAlpha(alpha)
                    .presentMode(VK_PRESENT_MODE_FIFO_KHR).clipped(true).oldSwapchain(VK_NULL_HANDLE);
                LongBuffer swapOut = stack.mallocLong(1);
                vk(vkCreateSwapchainKHR(device, sci, null, swapOut), "vkCreateSwapchainKHR");
                swapchain = swapOut.get(0);
                IntBuffer imageCount = stack.ints(0);
                vk(vkGetSwapchainImagesKHR(device, swapchain, imageCount, null), "vkGetSwapchainImagesKHR(count)");
                if (imageCount.get(0) == 0) throw new IllegalStateException("Swapchain returned no images");
                LongBuffer images = stack.mallocLong(imageCount.get(0));
                vk(vkGetSwapchainImagesKHR(device, swapchain, imageCount, images), "vkGetSwapchainImagesKHR(list)");
                imageHandles = new long[imageCount.get(0)]; images.get(0, imageHandles);
                renderFinished = new long[imageHandles.length];
                for (int i = 0; i < renderFinished.length; i++) {
                    LongBuffer sem = stack.mallocLong(1);
                    vk(vkCreateSemaphore(device, VkSemaphoreCreateInfo.calloc(stack).sType(VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO), null, sem), "vkCreateSemaphore(render)");
                    renderFinished[i] = sem.get(0);
                }
                LongBuffer sem = stack.mallocLong(1);
                vk(vkCreateSemaphore(device, VkSemaphoreCreateInfo.calloc(stack).sType(VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO), null, sem), "vkCreateSemaphore(acquire)");
                imageAvailable = sem.get(0);
                LongBuffer poolOut = stack.mallocLong(1);
                vk(vkCreateCommandPool(device, VkCommandPoolCreateInfo.calloc(stack).sType(VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO)
                    .flags(VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT).queueFamilyIndex(family), null, poolOut), "vkCreateCommandPool");
                commandPool = poolOut.get(0);
                PointerBuffer commandOut = stack.mallocPointer(1);
                vk(vkAllocateCommandBuffers(device, VkCommandBufferAllocateInfo.calloc(stack).sType(VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO)
                    .commandPool(commandPool).level(VK_COMMAND_BUFFER_LEVEL_PRIMARY).commandBufferCount(1), commandOut), "vkAllocateCommandBuffers");
                VkCommandBuffer command = new VkCommandBuffer(commandOut.get(0), device);
                LongBuffer fenceOut = stack.mallocLong(1);
                vk(vkCreateFence(device, VkFenceCreateInfo.calloc(stack).sType(VK_STRUCTURE_TYPE_FENCE_CREATE_INFO).flags(VK_FENCE_CREATE_SIGNALED_BIT), null, fenceOut), "vkCreateFence");
                fence = fenceOut.get(0);
                System.out.println("Vulkan presentation: surface=" + width + "x" + height + " format=" + format.format() + " swapchainImages=" + imageHandles.length + "; presenting " + frameLimit + " frames");
                System.out.flush();
                SDL_Event event = SDL_Event.calloc();
                try {
                    while (completed < frameLimit) {
                        while (SDL_PollEvent(event)) if (event.type() == SDL_EVENT_QUIT) throw new IllegalStateException("SDL window closed before frame limit");
                        try (MemoryStack frameStack = MemoryStack.stackPush()) {
                        vk(vkWaitForFences(device, fence, true, 5_000_000_000L), "vkWaitForFences");
                        IntBuffer imageIndex = frameStack.ints(0);
                        long acquireStart = System.nanoTime();
                        int acquire = VK_TIMEOUT, acquireAttempts = 0;
                        boolean loggedTimeout = false;
                        long acquireDeadline = acquireStart + ACQUIRE_DEADLINE_NS;
                        do {
                            long remaining = acquireDeadline - System.nanoTime();
                            if (remaining <= 0) break;
                            long timeout = Math.min(ACQUIRE_SLICE_NS, remaining);
                            acquire = vkAcquireNextImageKHR(device, swapchain, timeout, imageAvailable, VK_NULL_HANDLE, imageIndex);
                            acquireAttempts++;
                            if (acquire == VK_SUCCESS || acquire == VK_SUBOPTIMAL_KHR) break;
                            if (acquire != VK_TIMEOUT) {
                                System.err.printf("vkAcquireNextImageKHR failed result=%d attempts=%d elapsed_ms=%.3f%n", acquire, acquireAttempts, (System.nanoTime() - acquireStart) / 1_000_000.0);
                                vk(acquire, "vkAcquireNextImageKHR");
                            }
                            if (!loggedTimeout) {
                                System.err.printf("vkAcquireNextImageKHR transient VK_TIMEOUT attempt=%d elapsed_ms=%.3f%n", acquireAttempts, (System.nanoTime() - acquireStart) / 1_000_000.0);
                                loggedTimeout = true;
                            }
                            while (SDL_PollEvent(event)) if (event.type() == SDL_EVENT_QUIT) throw new IllegalStateException("SDL window closed before frame limit");
                            SDL_Delay(10);
                        } while (true);
                        if (acquire != VK_SUCCESS && acquire != VK_SUBOPTIMAL_KHR) {
                            long elapsedNs = System.nanoTime() - acquireStart;
                            System.err.printf("vkAcquireNextImageKHR deadline expired result=%d attempts=%d elapsed_ms=%.3f%n", acquireAttempts == 0 ? VK_TIMEOUT : acquire, acquireAttempts, elapsedNs / 1_000_000.0);
                            vk(acquireAttempts == 0 ? VK_TIMEOUT : acquire, "vkAcquireNextImageKHR");
                        }
                        int index = imageIndex.get(0);
                        if (index < 0 || index >= imageHandles.length) throw new IllegalStateException("Invalid acquired swapchain image index " + index);
                        if (acquireAttempts > 1) System.out.printf("vkAcquireNextImageKHR acquired image=%d after attempts=%d elapsed_ms=%.3f%n", index, acquireAttempts, (System.nanoTime() - acquireStart) / 1_000_000.0);
                        vk(vkResetFences(device, fence), "vkResetFences");
                        vk(vkResetCommandBuffer(command, 0), "vkResetCommandBuffer");
                        vk(vkBeginCommandBuffer(command, VkCommandBufferBeginInfo.calloc(frameStack).sType(VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO).flags(VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT)), "vkBeginCommandBuffer");
                        VkImageSubresourceRange range = VkImageSubresourceRange.calloc(frameStack).aspectMask(VK_IMAGE_ASPECT_COLOR_BIT).baseMipLevel(0).levelCount(1).baseArrayLayer(0).layerCount(1);
                        VkImageMemoryBarrier.Buffer barrier = VkImageMemoryBarrier.calloc(1, frameStack);
                        barrier.get(0).sType(VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER).srcAccessMask(0).dstAccessMask(VK_ACCESS_TRANSFER_WRITE_BIT)
                            .oldLayout(VK_IMAGE_LAYOUT_UNDEFINED).newLayout(VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL)
                            .srcQueueFamilyIndex(VK_QUEUE_FAMILY_IGNORED).dstQueueFamilyIndex(VK_QUEUE_FAMILY_IGNORED).image(imageHandles[index]).subresourceRange(range);
                        vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT, 0, null, null, barrier);
                        VkClearColorValue color = VkClearColorValue.calloc(frameStack).float32(0, (completed % 60) / 60.0f).float32(1, 0.25f).float32(2, 0.65f).float32(3, 1.0f);
                        vkCmdClearColorImage(command, imageHandles[index], VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, color, range);
                        barrier.get(0).srcAccessMask(VK_ACCESS_TRANSFER_WRITE_BIT).dstAccessMask(0).oldLayout(VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL).newLayout(VK_IMAGE_LAYOUT_PRESENT_SRC_KHR);
                        vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, 0, null, null, barrier);
                        vk(vkEndCommandBuffer(command), "vkEndCommandBuffer");
                        VkSubmitInfo submit = VkSubmitInfo.calloc(frameStack).sType(VK_STRUCTURE_TYPE_SUBMIT_INFO)
                            .waitSemaphoreCount(1).pWaitSemaphores(frameStack.longs(imageAvailable))
                            .pWaitDstStageMask(frameStack.ints(VK_PIPELINE_STAGE_TRANSFER_BIT))
                            .pCommandBuffers(frameStack.pointers(command.address())).pSignalSemaphores(frameStack.longs(renderFinished[index]));
                        vk(vkQueueSubmit(queue, submit, fence), "vkQueueSubmit");
                        VkPresentInfoKHR present = VkPresentInfoKHR.calloc(frameStack).sType(VK_STRUCTURE_TYPE_PRESENT_INFO_KHR)
                            .pWaitSemaphores(frameStack.longs(renderFinished[index])).swapchainCount(1)
                            .pSwapchains(frameStack.longs(swapchain)).pImageIndices(frameStack.ints(index));
                        int result = vkQueuePresentKHR(queue, present);
                        vk(vkWaitForFences(device, fence, true, 5_000_000_000L), "vkWaitForFences(present)");
                        if (result != VK_SUCCESS && result != VK_SUBOPTIMAL_KHR) vk(result, "vkQueuePresentKHR");
                        completed++;
                        }
                    }
                } finally { event.free(); }
            }
            System.out.println("PRESENTATION_PASS frames=" + completed);
            return completed;
        } catch (Throwable t) {
            primary = t;
            throw t;
        } finally {
            Throwable cleanupFailure = null;
            if (device != null) {
                try { vk(vkDeviceWaitIdle(device), "cleanup vkDeviceWaitIdle"); } catch (Throwable t) { cleanupFailure = t; }
                if (allocator != NULL) { vmaDestroyAllocator(allocator); System.out.println("VMA allocator destroyed"); }
                if (fence != NULL) vkDestroyFence(device, fence, null);
                if (renderFinished != null) for (long h : renderFinished) if (h != NULL) vkDestroySemaphore(device, h, null);
                if (imageAvailable != NULL) vkDestroySemaphore(device, imageAvailable, null);
                if (commandPool != NULL) vkDestroyCommandPool(device, commandPool, null);
                if (swapchain != NULL) vkDestroySwapchainKHR(device, swapchain, null);
                vkDestroyDevice(device, null);
            }
            if (surface != NULL && instance != null) SDL_Vulkan_DestroySurface(instance, surface, null);
            if (instance != null) vkDestroyInstance(instance, null);
            if (window != NULL) SDL_DestroyWindow(window);
            if (sdlInitialized) {
                SDL_Vulkan_UnloadLibrary();
                SDL_Quit();
            }
            VK.destroy();
            if (cleanupFailure != null) {
                if (primary != null) primary.addSuppressed(cleanupFailure); else throw new IllegalStateException("Vulkan cleanup failed", cleanupFailure);
            }
        }
    }

}
