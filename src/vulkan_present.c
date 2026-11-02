/* Uses the existing nxvk VI WSI design (MIT, PalindromicBreadLoaf, 2026).
 * SDL3 owns input/window state; Mesa NVK owns the native swapchain. */
#define SDL_MAIN_HANDLED
#include "platform.h"
#include <SDL3/SDL.h>
#include <SDL3/SDL_main.h>
#include <SDL3/SDL_vulkan.h>
#include <vulkan/vulkan.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern PFN_vkVoidFunction vkGetInstanceProcAddr(VkInstance,const char *);
#define INST(X) X(DestroyInstance) X(EnumeratePhysicalDevices) X(GetPhysicalDeviceProperties) X(GetPhysicalDeviceFeatures2) X(GetPhysicalDeviceQueueFamilyProperties) X(EnumerateDeviceExtensionProperties) X(GetDeviceProcAddr) X(CreateDevice)
#define WSI(X) X(GetPhysicalDeviceSurfaceSupportKHR) X(GetPhysicalDeviceSurfaceFormatsKHR) X(GetPhysicalDeviceSurfaceCapabilitiesKHR) X(DestroySurfaceKHR)
#define DEV(X) X(DestroyDevice) X(GetDeviceQueue) X(DeviceWaitIdle) X(CreateSwapchainKHR) X(DestroySwapchainKHR) X(GetSwapchainImagesKHR) X(AcquireNextImageKHR) X(QueuePresentKHR) X(CreateCommandPool) X(DestroyCommandPool) X(AllocateCommandBuffers) X(ResetCommandBuffer) X(BeginCommandBuffer) X(EndCommandBuffer) X(CmdPipelineBarrier) X(CmdClearColorImage) X(CreateSemaphore) X(DestroySemaphore) X(CreateFence) X(DestroyFence) X(WaitForFences) X(ResetFences) X(QueueSubmit) X(QueueWaitIdle)
#define DECL(n) PFN_vk##n n;
typedef struct {INST(DECL) WSI(DECL) DEV(DECL)} Dispatch;
#define TRY(call) do{VkResult result=(call);if(result!=VK_SUCCESS){sc_log("%s -> %d\n",#call,result);goto cleanup;}}while(0)

static void json_string(FILE *f,const char *s){
    fputc('"',f);for(;*s;s++){unsigned char c=(unsigned char)*s;if(c=='"'||c=='\\'){fputc('\\',f);fputc(c,f);}else if(c<32)fprintf(f,"\\u%04x",c);else fputc(c,f);}fputc('"',f);
}
static bool has_extension(const VkExtensionProperties *extensions,uint32_t n,const char *name){
    for(uint32_t i=0;i<n;i++)if(!strcmp(extensions[i].extensionName,name))return true;
    return false;
}
static bool profile(Dispatch *d,VkPhysicalDevice physical) {
    VkPhysicalDeviceProperties props;d->GetPhysicalDeviceProperties(physical,&props);
    VkPhysicalDeviceVertexAttributeDivisorFeaturesEXT divisor={.sType=VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VERTEX_ATTRIBUTE_DIVISOR_FEATURES_EXT};
    VkPhysicalDeviceSynchronization2Features sync={.sType=VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_SYNCHRONIZATION_2_FEATURES,.pNext=&divisor};
    VkPhysicalDeviceVulkan12Features f12={.sType=VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES,.pNext=&sync};
    VkPhysicalDeviceVulkan11Features f11={.sType=VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_1_FEATURES,.pNext=&f12};
    VkPhysicalDeviceFeatures2 f2={.sType=VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2,.pNext=&f11};
    d->GetPhysicalDeviceFeatures2(physical,&f2);
    const char *names[]={"multiDrawIndirect","drawIndirectFirstInstance","samplerAnisotropy","shaderDrawParameters","timelineSemaphore","hostQueryReset","synchronization2","vertexAttributeInstanceRateDivisor"};
    VkBool32 values[]={f2.features.multiDrawIndirect,f2.features.drawIndirectFirstInstance,f2.features.samplerAnisotropy,f11.shaderDrawParameters,f12.timelineSemaphore,f12.hostQueryReset,sync.synchronization2,divisor.vertexAttributeInstanceRateDivisor};
    const char *needed[]={"VK_KHR_synchronization2","VK_EXT_vertex_attribute_divisor","VK_KHR_swapchain"};
    uint32_t count=0;VkResult r=d->EnumerateDeviceExtensionProperties(physical,NULL,&count,NULL);
    if(r!=VK_SUCCESS){sc_log("Device extension count -> %d\n",r);return false;}
    VkExtensionProperties *extensions=calloc(count?count:1,sizeof(*extensions));if(!extensions)return false;
    r=d->EnumerateDeviceExtensionProperties(physical,NULL,&count,extensions);
    if(r!=VK_SUCCESS){free(extensions);return false;}
    bool ok=props.apiVersion>=VK_API_VERSION_1_2;
    sc_log("Snapshot 6 Vulkan base profile: GPU=%s API=%u.%u.%u\n",props.deviceName,VK_VERSION_MAJOR(props.apiVersion),VK_VERSION_MINOR(props.apiVersion),VK_VERSION_PATCH(props.apiVersion));
    FILE *f=fopen(SC_LOGS "/snapshot-vulkan.json","w");
    if(f){fprintf(f,"{\"target\":\"26.4-snapshot-6\",\"gpu\":");json_string(f,props.deviceName);fprintf(f,",\"api_version\":%u,\"features\":{",props.apiVersion);}
    for(unsigned i=0;i<8;i++){
        sc_log("%s=%u\n",names[i],values[i]);if(!values[i])ok=false;
        if(f){if(i)fputc(',',f);json_string(f,names[i]);fprintf(f,":%s",values[i]?"true":"false");}
    }
    if(f)fprintf(f,"},\"extensions\":[");
    for(uint32_t i=0;i<count;i++)if(f){if(i)fputc(',',f);json_string(f,extensions[i].extensionName);}
    for(unsigned i=0;i<3;i++){bool present=has_extension(extensions,count,needed[i]);sc_log("%s=%s\n",needed[i],present?"YES":"MISSING");if(!present)ok=false;}
    if(f){fprintf(f,"],\"base_profile_supported\":%s,\"swapchain_presentation\":\"NOT TESTED by this profile\",\"minecraft_title\":\"NOT TESTED on Horizon\"}\n",ok?"true":"false");fclose(f);}
    free(extensions);sc_log("Required base profile: %s (rendering/title still separate)\n",ok?"PASS":"INCOMPATIBLE");return ok;
}

static bool run(bool present) {
    Dispatch d={0};SDL_Window *window=NULL;SDL_Gamepad *gamepad=NULL;
    bool sdl=false,screen=false,submitted=false;unsigned frames=0;bool complete=false;
    VkInstance instance=VK_NULL_HANDLE;VkDevice device=VK_NULL_HANDLE;VkSurfaceKHR surface=VK_NULL_HANDLE;
    VkSwapchainKHR chain=VK_NULL_HANDLE;VkCommandPool pool=VK_NULL_HANDLE;VkSemaphore acquired=VK_NULL_HANDLE,*rendered=NULL;
    uint32_t chain_image_count=0;
    VkFence fence=VK_NULL_HANDLE;VkImage *images=NULL;
    const char *const *extensions=NULL;Uint32 extension_count=0;
    if(present){
        sc_log("Entering SDL3 / Vulkan-only window / VI surface test\n");sc_console(false);screen=true;
        SDL_SetMainReady();
        sdl=true;
        if(!SDL_Init(SDL_INIT_VIDEO|SDL_INIT_GAMEPAD)){sc_log("SDL_Init: %s\n",SDL_GetError());goto cleanup;}
        window=SDL_CreateWindow("Switchcraft Vulkan 26.4-snapshot-6",1280,720,SDL_WINDOW_VULKAN);
        if(!window){sc_log("SDL_CreateWindow: %s\n",SDL_GetError());goto cleanup;}
        sc_log("SDL version=%d driver=%s\n",SDL_GetVersion(),SDL_GetCurrentVideoDriver());
        int n=0;SDL_JoystickID *ids=SDL_GetGamepads(&n);
        if(ids&&n>0)gamepad=SDL_OpenGamepad(ids[0]);
        SDL_free(ids);
        if(gamepad)sc_log("SDL gamepad: %s\n",SDL_GetGamepadName(gamepad));
        extensions=SDL_Vulkan_GetInstanceExtensions(&extension_count);
        if(!extensions||!extension_count){sc_log("No SDL Vulkan instance extensions: %s\n",SDL_GetError());goto cleanup;}
    }
    PFN_vkCreateInstance create=(PFN_vkCreateInstance)vkGetInstanceProcAddr(NULL,"vkCreateInstance");
    if(!create){sc_log("No Vulkan create instance function\n");goto cleanup;}
    VkApplicationInfo app={.sType=VK_STRUCTURE_TYPE_APPLICATION_INFO,.pApplicationName="Switchcraft snapshot 6",.apiVersion=VK_API_VERSION_1_2};
    VkInstanceCreateInfo ici={.sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,.pApplicationInfo=&app,.enabledExtensionCount=extension_count,.ppEnabledExtensionNames=extensions};
    TRY(create(&ici,NULL,&instance));
#define LOADI(n) d.n=(PFN_vk##n)vkGetInstanceProcAddr(instance,"vk" #n);if(!d.n){sc_log("Missing vk" #n "\n");goto cleanup;}
    INST(LOADI)
    if(present){WSI(LOADI)}
    if(present&&!SDL_Vulkan_CreateSurface(window,instance,NULL,&surface)){sc_log("SDL_Vulkan_CreateSurface: %s\n",SDL_GetError());goto cleanup;}
    uint32_t nphysical=0;TRY(d.EnumeratePhysicalDevices(instance,&nphysical,NULL));
    if(!nphysical||nphysical>16){sc_log("Physical device count=%u\n",nphysical);goto cleanup;}
    VkPhysicalDevice physicals[16];TRY(d.EnumeratePhysicalDevices(instance,&nphysical,physicals));
    VkPhysicalDevice physical=physicals[0];
    /* Keep the presentation smoke test independent of full snapshot support. */
    bool compatible=profile(&d,physical);if(!present){complete=compatible;goto cleanup;}
    uint32_t nqueues=0;d.GetPhysicalDeviceQueueFamilyProperties(physical,&nqueues,NULL);
    VkQueueFamilyProperties *queues=calloc(nqueues?nqueues:1,sizeof(*queues));if(!queues)goto cleanup;
    d.GetPhysicalDeviceQueueFamilyProperties(physical,&nqueues,queues);uint32_t family=UINT32_MAX;
    for(uint32_t i=0;i<nqueues;i++){
        VkBool32 supported=0;VkResult r=d.GetPhysicalDeviceSurfaceSupportKHR(physical,i,surface,&supported);
        if(r==VK_SUCCESS&&supported&&queues[i].queueCount&&(queues[i].queueFlags&VK_QUEUE_GRAPHICS_BIT)){family=i;break;}
    }
    free(queues);if(family==UINT32_MAX){sc_log("No graphics/present queue\n");goto cleanup;}
    float priority=1;VkDeviceQueueCreateInfo qci={.sType=VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,.queueFamilyIndex=family,.queueCount=1,.pQueuePriorities=&priority};
    const char *device_exts[]={"VK_KHR_swapchain"};
    VkDeviceCreateInfo dc={.sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,.queueCreateInfoCount=1,.pQueueCreateInfos=&qci,.enabledExtensionCount=1,.ppEnabledExtensionNames=device_exts};
    TRY(d.CreateDevice(physical,&dc,NULL,&device));
#define LOADD(n) d.n=(PFN_vk##n)d.GetDeviceProcAddr(device,"vk" #n);if(!d.n){sc_log("Missing vk" #n "\n");goto cleanup;}
    DEV(LOADD)
    VkQueue queue;d.GetDeviceQueue(device,family,0,&queue);
    VkSurfaceCapabilitiesKHR caps;TRY(d.GetPhysicalDeviceSurfaceCapabilitiesKHR(physical,surface,&caps));
    if(!(caps.supportedUsageFlags&VK_IMAGE_USAGE_TRANSFER_DST_BIT)){sc_log("Surface lacks transfer-destination usage\n");goto cleanup;}
    VkExtent2D extent=caps.currentExtent;
    if(extent.width==UINT32_MAX){extent=(VkExtent2D){1280,720};if(extent.width<caps.minImageExtent.width)extent.width=caps.minImageExtent.width;if(extent.width>caps.maxImageExtent.width)extent.width=caps.maxImageExtent.width;if(extent.height<caps.minImageExtent.height)extent.height=caps.minImageExtent.height;if(extent.height>caps.maxImageExtent.height)extent.height=caps.maxImageExtent.height;}
    uint32_t count=0;TRY(d.GetPhysicalDeviceSurfaceFormatsKHR(physical,surface,&count,NULL));
    if(!count||count>256)goto cleanup;
    VkSurfaceFormatKHR *formats=calloc(count,sizeof(*formats));if(!formats)goto cleanup;
    VkResult format_result=d.GetPhysicalDeviceSurfaceFormatsKHR(physical,surface,&count,formats);
    if(format_result!=VK_SUCCESS){free(formats);goto cleanup;}
    VkSurfaceFormatKHR format=formats[0];
    for(uint32_t i=0;i<count;i++)if(formats[i].format==VK_FORMAT_B8G8R8A8_UNORM||formats[i].format==VK_FORMAT_R8G8B8A8_UNORM){format=formats[i];break;}
    free(formats);if(format.format==VK_FORMAT_UNDEFINED)format.format=VK_FORMAT_B8G8R8A8_UNORM;
    uint32_t image_count=caps.minImageCount+1;if(caps.maxImageCount&&image_count>caps.maxImageCount)image_count=caps.maxImageCount;
    VkCompositeAlphaFlagBitsKHR alpha=VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR;
    if(!(caps.supportedCompositeAlpha&alpha))alpha=(VkCompositeAlphaFlagBitsKHR)(caps.supportedCompositeAlpha&(~caps.supportedCompositeAlpha+1));
    VkSwapchainCreateInfoKHR sci={.sType=VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR,.surface=surface,.minImageCount=image_count,.imageFormat=format.format,.imageColorSpace=format.colorSpace,
        .imageExtent=extent,.imageArrayLayers=1,.imageUsage=VK_IMAGE_USAGE_TRANSFER_DST_BIT,.imageSharingMode=VK_SHARING_MODE_EXCLUSIVE,.preTransform=caps.currentTransform,.compositeAlpha=alpha,.presentMode=VK_PRESENT_MODE_FIFO_KHR,.clipped=VK_TRUE};
    TRY(d.CreateSwapchainKHR(device,&sci,NULL,&chain));
    count=0;TRY(d.GetSwapchainImagesKHR(device,chain,&count,NULL));if(!count||count>32)goto cleanup;
    images=calloc(count,sizeof(*images));if(!images)goto cleanup;TRY(d.GetSwapchainImagesKHR(device,chain,&count,images));
    chain_image_count=count;
    VkCommandPoolCreateInfo pci={.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT,.queueFamilyIndex=family};
    TRY(d.CreateCommandPool(device,&pci,NULL,&pool));
    VkCommandBuffer command;VkCommandBufferAllocateInfo ai={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,.commandPool=pool,.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY,.commandBufferCount=1};TRY(d.AllocateCommandBuffers(device,&ai,&command));
    VkSemaphoreCreateInfo sem={.sType=VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO};TRY(d.CreateSemaphore(device,&sem,NULL,&acquired));
    rendered=calloc(chain_image_count,sizeof(*rendered));if(!rendered)goto cleanup;
    for(uint32_t i=0;i<chain_image_count;i++)TRY(d.CreateSemaphore(device,&sem,NULL,&rendered[i]));
    VkFenceCreateInfo fi={.sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};TRY(d.CreateFence(device,&fi,NULL,&fence));
    sc_log("VI swapchain %ux%u images=%u format=%u; plus/Start or B exits\n",extent.width,extent.height,count,format.format);
    bool quit=false;
    while(appletMainLoop()&&!quit&&frames<300){
        SDL_Event event;while(SDL_PollEvent(&event)){
            if(event.type==SDL_EVENT_QUIT)quit=true;
            if(event.type==SDL_EVENT_GAMEPAD_BUTTON_DOWN){sc_log("SDL gamepad button=%u\n",event.gbutton.button);if(event.gbutton.button==SDL_GAMEPAD_BUTTON_START||event.gbutton.button==SDL_GAMEPAD_BUTTON_EAST)quit=true;}
        }
        if(quit)break;
        uint32_t index=0;VkResult r=d.AcquireNextImageKHR(device,chain,5000000000ull,acquired,VK_NULL_HANDLE,&index);
        if(r!=VK_SUCCESS&&r!=VK_SUBOPTIMAL_KHR){sc_log("AcquireNextImageKHR frame=%u -> %d\n",frames,r);break;}
        if(index>=count){sc_log("Swapchain returned invalid image index\n");break;}
        TRY(d.ResetCommandBuffer(command,0));VkCommandBufferBeginInfo begin={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT};TRY(d.BeginCommandBuffer(command,&begin));
        VkImageSubresourceRange range={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};
        VkImageMemoryBarrier barrier={.sType=VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER,.dstAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT,.oldLayout=VK_IMAGE_LAYOUT_UNDEFINED,.newLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
            .srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.image=images[index],.subresourceRange=range};
        d.CmdPipelineBarrier(command,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,NULL,0,NULL,1,&barrier);
        VkClearColorValue color={.float32={(frames%120)/120.0f,0.2f,0.8f,1}};
        d.CmdClearColorImage(command,images[index],VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,&color,1,&range);
        barrier.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;barrier.dstAccessMask=0;barrier.oldLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;barrier.newLayout=VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;
        d.CmdPipelineBarrier(command,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,0,0,NULL,0,NULL,1,&barrier);TRY(d.EndCommandBuffer(command));
        VkPipelineStageFlags stage=VK_PIPELINE_STAGE_TRANSFER_BIT;
        VkSubmitInfo submit={.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO,.waitSemaphoreCount=1,.pWaitSemaphores=&acquired,.pWaitDstStageMask=&stage,.commandBufferCount=1,.pCommandBuffers=&command,.signalSemaphoreCount=1,.pSignalSemaphores=&rendered[index]};
        TRY(d.QueueSubmit(queue,1,&submit,fence));submitted=true;
        VkPresentInfoKHR pi={.sType=VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,.waitSemaphoreCount=1,.pWaitSemaphores=&rendered[index],.swapchainCount=1,.pSwapchains=&chain,.pImageIndices=&index};
        r=d.QueuePresentKHR(queue,&pi);
        VkResult wait=d.WaitForFences(device,1,&fence,VK_TRUE,5000000000ull);
        if(wait!=VK_SUCCESS){sc_log("Present fence -> %d; exiting without destroying pending objects\n",wait);return false;}
        /* Per-image present semaphore is reused only after reacquiring that image. */
        TRY(d.QueueWaitIdle(queue));submitted=false;TRY(d.ResetFences(device,1,&fence));
        if(r!=VK_SUCCESS&&r!=VK_SUBOPTIMAL_KHR){sc_log("QueuePresentKHR -> %d\n",r);break;}
        frames++;
    }
    complete=frames>0;
cleanup:
    if(submitted){sc_log("GPU work pending; application exits for process teardown\n");return false;}
    if(device&&d.DeviceWaitIdle)d.DeviceWaitIdle(device);
    if(fence&&d.DestroyFence)d.DestroyFence(device,fence,NULL);
    if(rendered&&d.DestroySemaphore)for(uint32_t i=0;i<chain_image_count;i++)if(rendered[i])d.DestroySemaphore(device,rendered[i],NULL);
    if(acquired&&d.DestroySemaphore)d.DestroySemaphore(device,acquired,NULL);
    if(pool&&d.DestroyCommandPool)d.DestroyCommandPool(device,pool,NULL);
    if(chain&&d.DestroySwapchainKHR)d.DestroySwapchainKHR(device,chain,NULL);
    if(device&&d.DestroyDevice)d.DestroyDevice(device,NULL);
    if(surface&&d.DestroySurfaceKHR)d.DestroySurfaceKHR(instance,surface,NULL);
    if(instance&&d.DestroyInstance)d.DestroyInstance(instance,NULL);
    free(images);free(rendered);if(gamepad)SDL_CloseGamepad(gamepad);if(window)SDL_DestroyWindow(window);if(sdl)SDL_Quit();if(screen)sc_console(true);
    sc_log("%s result=%s; presented frames=%u (not Minecraft title verification)\n",present?"SDL3 VI presentation":"Snapshot base profile",complete?"PASS":"NOT PASSED",frames);
    return true;
}
int main(void){
    sc_init("vulkan-present");sc_log("26.4-snapshot-6 Vulkan-only bring-up\nA: exact base feature profile | X: SDL3 VI swapchain / gamepad\nB: diagnostics | +: exit\n");u64 keys;
    while(sc_frame(&keys)){
        if((keys&HidNpadButton_A)&&!run(false))break;
        if((keys&HidNpadButton_X)&&!run(true))break;
        if((keys&HidNpadButton_B)&&sc_chain("switch-diagnostics"))break;
    }
    sc_exit();return 0;
}
