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
#include <math.h>
#include <errno.h>
#include <switchcraft/native_lookup.h>

extern PFN_vkVoidFunction vkGetInstanceProcAddr(VkInstance,const char *);
#define INST(X) X(DestroyInstance) X(EnumeratePhysicalDevices) X(GetPhysicalDeviceProperties) X(GetPhysicalDeviceFeatures2) X(GetPhysicalDeviceQueueFamilyProperties) X(EnumerateDeviceExtensionProperties) X(GetDeviceProcAddr) X(CreateDevice)
#define WSI(X) X(GetPhysicalDeviceSurfaceSupportKHR) X(GetPhysicalDeviceSurfaceFormatsKHR) X(GetPhysicalDeviceSurfaceCapabilitiesKHR) X(DestroySurfaceKHR)
#define DEV(X) X(DestroyDevice) X(GetDeviceQueue) X(DeviceWaitIdle) X(CreateSwapchainKHR) X(DestroySwapchainKHR) X(GetSwapchainImagesKHR) X(AcquireNextImageKHR) X(QueuePresentKHR) X(CreateCommandPool) X(DestroyCommandPool) X(AllocateCommandBuffers) X(ResetCommandBuffer) X(BeginCommandBuffer) X(EndCommandBuffer) X(CmdPipelineBarrier) X(CmdClearColorImage) X(CreateSemaphore) X(DestroySemaphore) X(CreateFence) X(DestroyFence) X(WaitForFences) X(ResetFences) X(QueueSubmit)
#define DECL(n) PFN_vk##n n;
typedef struct {INST(DECL) WSI(DECL) DEV(DECL)} Dispatch;
#define TRY(call) do{VkResult result=(call);if(result!=VK_SUCCESS){failed=true;last_vk_result=result;failure_reason="vulkan_call_failed";sc_log("%s -> %d\n",#call,result);goto cleanup;}}while(0)

static void write_attempt_result(bool present,const char *result,const char *reason,
                                 unsigned frames,u64 attempt,u64 elapsed_ns,u64 frame_total_ns,
                                 u64 frame_min_ns,u64 frame_max_ns,int last_vk_result) {
    char body[1200],path[256];
    double avg_ms=frames?(double)frame_total_ns/(double)frames/1000000.0:0.0;
    double min_ms=frames?(double)frame_min_ns/1000000.0:0.0;
    double max_ms=frames?(double)frame_max_ns/1000000.0:0.0;
    int n=snprintf(body,sizeof(body),"{\"attempt\":%llu,\"mode\":\"%s\",\"result\":\"%s\",\"reason\":\"%s\",\"frames\":%u,\"elapsed_ms\":%.3f,\"frame_turnaround_avg_ms\":%.3f,\"frame_turnaround_min_ms\":%.3f,\"frame_turnaround_max_ms\":%.3f,\"last_vk_result\":%d,\"minecraft_title\":\"NOT TESTED on Horizon\"}\n",
        (unsigned long long)attempt,present?"sdl3_vi_presentation":"snapshot_base_profile",result,reason,frames,
        (double)elapsed_ns/1000000.0,avg_ms,min_ms,max_ms,last_vk_result);
    if(n<0||(size_t)n>=sizeof(body))return;
    for(unsigned i=0;i<2;i++) {
        if(i)snprintf(path,sizeof(path),SC_LOGS "/vulkan-present-result-%llu.json",(unsigned long long)attempt);
        else snprintf(path,sizeof(path),SC_LOGS "/vulkan-present-result.json");
        FILE *f=fopen(path,"w");
        if(!f){sc_log("Could not write presentation result errno=%d\n",errno);continue;}
        bool ok=fwrite(body,1,(size_t)n,f)==(size_t)n;
        if(fclose(f)!=0)ok=false;
        if(!ok)sc_log("Presentation result write failed: %s\n",path);
    }
}

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
    if(count>65536){sc_log("Device extension count exceeds limit: %u\n",count);return false;}
    VkExtensionProperties *extensions=calloc(count?count:1,sizeof(*extensions));if(!extensions)return false;
    r=d->EnumerateDeviceExtensionProperties(physical,NULL,&count,extensions);
    if(r!=VK_SUCCESS){sc_log("Device extension enumeration -> %d\n",r);free(extensions);return false;}
    bool ok=props.apiVersion>=VK_API_VERSION_1_2;
    sc_log("Snapshot 6 Vulkan base profile: GPU=%s API=%u.%u.%u\n",props.deviceName,VK_VERSION_MAJOR(props.apiVersion),VK_VERSION_MINOR(props.apiVersion),VK_VERSION_PATCH(props.apiVersion));
    sc_log("Device vendor=0x%x device=0x%x type=%u driver=0x%x\n",props.vendorID,props.deviceID,props.deviceType,props.driverVersion);
    FILE *f=fopen(SC_LOGS "/snapshot-vulkan.json","w");
    if(f){fprintf(f,"{\"target\":\"26.4-snapshot-6\",\"gpu\":");json_string(f,props.deviceName);fprintf(f,",\"api_version\":%u,\"vendor_id\":%u,\"device_id\":%u,\"device_type\":%u,\"driver_version\":%u,\"features\":{",props.apiVersion,props.vendorID,props.deviceID,props.deviceType,props.driverVersion);}
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

static bool gpu_process_exit_required;

static bool run(bool present) {
    Dispatch d={0};SDL_Window *window=NULL;SDL_Gamepad *gamepad=NULL;
    bool sdl=false,screen=false,failed=false,submitted=false;unsigned frames=0;bool complete=false;
    const char *failure_reason="initialization_error",*exit_reason="frame_limit";
    int last_vk_result=VK_SUCCESS;
    u64 attempt_start=armGetSystemTick(),frame_total_ns=0,frame_min_ns=UINT64_MAX,frame_max_ns=0;
    VkInstance instance=VK_NULL_HANDLE;VkDevice device=VK_NULL_HANDLE;VkSurfaceKHR surface=VK_NULL_HANDLE;
    VkSwapchainKHR chain=VK_NULL_HANDLE;VkCommandPool pool=VK_NULL_HANDLE;VkSemaphore acquired=VK_NULL_HANDLE,*rendered=NULL;
    uint32_t chain_image_count=0;
    VkFence fence=VK_NULL_HANDLE;VkImage *images=NULL;
    const char *const *extensions=NULL;Uint32 extension_count=0;
    write_attempt_result(present,"RUNNING","starting",0,attempt_start,0,0,0,0,VK_SUCCESS);
    if(present){
        sc_log("Entering SDL3 / Vulkan-only window / VI surface test\n");sc_console(false);screen=true;
        sc_log("Static native lookup SDL_CreateWindow=%s SDL_Vulkan_CreateSurface=%s vkGetInstanceProcAddr=%s\n",
            sc_horizon_native_lookup("SDL3","SDL_CreateWindow")?"present":"MISSING",
            sc_horizon_native_lookup("SDL3","SDL_Vulkan_CreateSurface")?"present":"MISSING",
            sc_horizon_native_lookup("vulkan","vkGetInstanceProcAddr")?"present":"MISSING");
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
    sc_log("STAGE vulkan-instance: create API 1.2 extensions=%u\n",extension_count);
    for(Uint32 i=0;i<extension_count;i++)sc_log("Instance extension[%u]=%s\n",i,extensions[i]);
    PFN_vkCreateInstance create=(PFN_vkCreateInstance)vkGetInstanceProcAddr(NULL,"vkCreateInstance");
    if(!create){sc_log("No Vulkan create instance function\n");goto cleanup;}
    VkApplicationInfo app={.sType=VK_STRUCTURE_TYPE_APPLICATION_INFO,.pApplicationName="Switchcraft snapshot 6",.apiVersion=VK_API_VERSION_1_2};
    VkInstanceCreateInfo ici={.sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,.pApplicationInfo=&app,.enabledExtensionCount=extension_count,.ppEnabledExtensionNames=extensions};
    TRY(create(&ici,NULL,&instance));
#define LOADI(n) d.n=(PFN_vk##n)vkGetInstanceProcAddr(instance,"vk" #n);if(!d.n){sc_log("Missing vk" #n "\n");goto cleanup;}
    INST(LOADI)
    if(present){WSI(LOADI)}
    if(present){sc_log("STAGE surface: SDL_Vulkan_CreateSurface\n");if(!SDL_Vulkan_CreateSurface(window,instance,NULL,&surface)){sc_log("SDL_Vulkan_CreateSurface: %s\n",SDL_GetError());goto cleanup;}}
    uint32_t nphysical=0;TRY(d.EnumeratePhysicalDevices(instance,&nphysical,NULL));
    if(!nphysical||nphysical>16){sc_log("Physical device count=%u\n",nphysical);goto cleanup;}
    VkPhysicalDevice physicals[16];TRY(d.EnumeratePhysicalDevices(instance,&nphysical,physicals));
    VkPhysicalDevice physical=physicals[0];
    /* Keep the presentation smoke test independent of full snapshot support. */
    bool compatible=profile(&d,physical);if(!present){complete=compatible;failed=!compatible;failure_reason=compatible?"profile_supported":"profile_incompatible";goto cleanup;}
    uint32_t nqueues=0;d.GetPhysicalDeviceQueueFamilyProperties(physical,&nqueues,NULL);
    VkQueueFamilyProperties *queues=calloc(nqueues?nqueues:1,sizeof(*queues));if(!queues)goto cleanup;
    d.GetPhysicalDeviceQueueFamilyProperties(physical,&nqueues,queues);uint32_t family=UINT32_MAX;
    for(uint32_t i=0;i<nqueues;i++){
        VkBool32 supported=0;VkResult r=d.GetPhysicalDeviceSurfaceSupportKHR(physical,i,surface,&supported);
        sc_log("Queue family=%u flags=0x%x count=%u surface_result=%d present=%u\n",i,queues[i].queueFlags,queues[i].queueCount,r,supported);
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
    sc_log("Surface min/max images=%u/%u usage=0x%x transforms=0x%x current=0x%x composite=0x%x\n",caps.minImageCount,caps.maxImageCount,caps.supportedUsageFlags,caps.supportedTransforms,caps.currentTransform,caps.supportedCompositeAlpha);
    if(!(caps.supportedUsageFlags&VK_IMAGE_USAGE_TRANSFER_DST_BIT)){sc_log("Surface lacks transfer-destination usage\n");goto cleanup;}
    VkExtent2D extent=caps.currentExtent;
    if(extent.width==UINT32_MAX){extent=(VkExtent2D){1280,720};if(extent.width<caps.minImageExtent.width)extent.width=caps.minImageExtent.width;if(extent.width>caps.maxImageExtent.width)extent.width=caps.maxImageExtent.width;if(extent.height<caps.minImageExtent.height)extent.height=caps.minImageExtent.height;if(extent.height>caps.maxImageExtent.height)extent.height=caps.maxImageExtent.height;}
    uint32_t count=0;TRY(d.GetPhysicalDeviceSurfaceFormatsKHR(physical,surface,&count,NULL));
    if(!count||count>256)goto cleanup;
    VkSurfaceFormatKHR *formats=calloc(count,sizeof(*formats));if(!formats)goto cleanup;
    VkResult format_result=d.GetPhysicalDeviceSurfaceFormatsKHR(physical,surface,&count,formats);
    if(format_result!=VK_SUCCESS){sc_log("Surface formats -> %d\n",format_result);free(formats);goto cleanup;}
    VkSurfaceFormatKHR format=formats[0];
    for(uint32_t i=0;i<count;i++)if(formats[i].format==VK_FORMAT_B8G8R8A8_UNORM||formats[i].format==VK_FORMAT_R8G8B8A8_UNORM){format=formats[i];break;}
    free(formats);if(format.format==VK_FORMAT_UNDEFINED)format.format=VK_FORMAT_B8G8R8A8_UNORM;
    uint32_t image_count=caps.minImageCount+1;if(caps.maxImageCount&&image_count>caps.maxImageCount)image_count=caps.maxImageCount;
    VkCompositeAlphaFlagBitsKHR alpha=VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR;
    if(!(caps.supportedCompositeAlpha&alpha))alpha=(VkCompositeAlphaFlagBitsKHR)(caps.supportedCompositeAlpha&(~caps.supportedCompositeAlpha+1));
    VkSwapchainCreateInfoKHR sci={.sType=VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR,.surface=surface,.minImageCount=image_count,.imageFormat=format.format,.imageColorSpace=format.colorSpace,
        .imageExtent=extent,.imageArrayLayers=1,.imageUsage=VK_IMAGE_USAGE_TRANSFER_DST_BIT,.imageSharingMode=VK_SHARING_MODE_EXCLUSIVE,.preTransform=caps.currentTransform,.compositeAlpha=alpha,.presentMode=VK_PRESENT_MODE_FIFO_KHR,.clipped=VK_TRUE};
    sc_log("STAGE swapchain: create FIFO extent=%ux%u requested_images=%u\n",extent.width,extent.height,image_count);
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
    sc_log("STAGE present: family=%u extent=%ux%u images=%u format=%u colorspace=%u FIFO alpha=0x%x; SDL Start/East exits\n",family,extent.width,extent.height,count,format.format,format.colorSpace,alpha);
    bool quit=false;
    while(appletMainLoop()&&!quit&&frames<300){
        SDL_Event event;while(SDL_PollEvent(&event)){
            if(event.type==SDL_EVENT_QUIT){quit=true;exit_reason="window_close";}
            if(event.type==SDL_EVENT_GAMEPAD_BUTTON_DOWN){const char *button=SDL_GetGamepadStringForButton((SDL_GamepadButton)event.gbutton.button);sc_log("SDL gamepad instance=%u button=%u name=%s\n",event.gbutton.which,event.gbutton.button,button?button:"unknown");if(event.gbutton.button==SDL_GAMEPAD_BUTTON_START||event.gbutton.button==SDL_GAMEPAD_BUTTON_EAST){quit=true;exit_reason="user_exit";}}
        }
        if(quit)break;
        u64 frame_start=armGetSystemTick();
        uint32_t index=0;VkResult r=d.AcquireNextImageKHR(device,chain,5000000000ull,acquired,VK_NULL_HANDLE,&index);
        if(r!=VK_SUCCESS&&r!=VK_SUBOPTIMAL_KHR){failed=true;last_vk_result=r;failure_reason="acquire_failed";sc_log("AcquireNextImageKHR frame=%u -> %d\n",frames,r);break;}
        if(index>=count){failed=true;failure_reason="invalid_swapchain_image";sc_log("Swapchain returned invalid image index=%u count=%u\n",index,count);break;}
        TRY(d.ResetCommandBuffer(command,0));VkCommandBufferBeginInfo begin={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT};TRY(d.BeginCommandBuffer(command,&begin));
        VkImageSubresourceRange range={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};
        VkImageMemoryBarrier barrier={.sType=VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER,.dstAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT,.oldLayout=VK_IMAGE_LAYOUT_UNDEFINED,.newLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
            .srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.image=images[index],.subresourceRange=range};
        d.CmdPipelineBarrier(command,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,NULL,0,NULL,1,&barrier);
        double seconds=(double)armTicksToNs(armGetSystemTick()-attempt_start)/1000000000.0;
        float phase=(float)(seconds*0.8);
        VkClearColorValue color={.float32={
            0.5f+0.5f*sinf(phase),
            0.5f+0.5f*sinf(phase-2.0943951f),
            0.5f+0.5f*sinf(phase-4.1887902f),1.0f}};
        d.CmdClearColorImage(command,images[index],VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,&color,1,&range);
        barrier.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;barrier.dstAccessMask=0;barrier.oldLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;barrier.newLayout=VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;
        d.CmdPipelineBarrier(command,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,0,0,NULL,0,NULL,1,&barrier);TRY(d.EndCommandBuffer(command));
        VkPipelineStageFlags stage=VK_PIPELINE_STAGE_TRANSFER_BIT;
        VkSubmitInfo submit={.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO,.waitSemaphoreCount=1,.pWaitSemaphores=&acquired,.pWaitDstStageMask=&stage,.commandBufferCount=1,.pCommandBuffers=&command,.signalSemaphoreCount=1,.pSignalSemaphores=&rendered[index]};
        TRY(d.QueueSubmit(queue,1,&submit,fence));submitted=true;
        VkPresentInfoKHR pi={.sType=VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,.waitSemaphoreCount=1,.pWaitSemaphores=&rendered[index],.swapchainCount=1,.pSwapchains=&chain,.pImageIndices=&index};
        r=d.QueuePresentKHR(queue,&pi);
        VkResult wait=d.WaitForFences(device,1,&fence,VK_TRUE,5000000000ull);
        if(wait!=VK_SUCCESS){failed=true;last_vk_result=wait;failure_reason="frame_fence_failed";sc_log("Present fence frame=%u -> %d\n",frames,wait);break;}
        submitted=false;
        if(r!=VK_SUCCESS&&r!=VK_SUBOPTIMAL_KHR){failed=true;last_vk_result=r;failure_reason="present_failed";sc_log("QueuePresentKHR frame=%u -> %d\n",frames,r);break;}
        /* The fence retires command-buffer use. The present semaphore belongs to
         * this swapchain image and is reused only after that image is reacquired. */
        u64 frame_ns=armTicksToNs(armGetSystemTick()-frame_start);
        frame_total_ns+=frame_ns;if(frame_ns<frame_min_ns)frame_min_ns=frame_ns;if(frame_ns>frame_max_ns)frame_max_ns=frame_ns;
        TRY(d.ResetFences(device,1,&fence));
        frames++;
    }
    if(!appletMainLoop()&&!quit)exit_reason="applet_exit";
    complete=frames==300&&!failed;
    if(!complete&&!failed)failure_reason=exit_reason;
cleanup:
    if(submitted) {
        write_attempt_result(present,"FAIL",failure_reason,frames,attempt_start,armTicksToNs(armGetSystemTick()-attempt_start),frame_total_ns,frame_min_ns,frame_max_ns,last_vk_result);
        sc_log("Unretired GPU submission: retaining resources for application-process termination.\n");
        gpu_process_exit_required=true;return false;
    }
    if(device&&d.DeviceWaitIdle){sc_log("STAGE cleanup: vkDeviceWaitIdle (once at teardown)\n");VkResult idle=d.DeviceWaitIdle(device);if(idle!=VK_SUCCESS){sc_log("vkDeviceWaitIdle -> %d; retaining GPU resources for process termination\n",idle);write_attempt_result(present,"FAIL","device_idle_failed",frames,attempt_start,armTicksToNs(armGetSystemTick()-attempt_start),frame_total_ns,frame_min_ns,frame_max_ns,idle);gpu_process_exit_required=true;return false;if(last_vk_result==VK_SUCCESS)last_vk_result=idle;failed=true;complete=false;if(!strcmp(failure_reason,"initialization_error"))failure_reason="device_idle_failed";}}
    if(fence&&d.DestroyFence)d.DestroyFence(device,fence,NULL);
    if(rendered&&d.DestroySemaphore)for(uint32_t i=0;i<chain_image_count;i++)if(rendered[i])d.DestroySemaphore(device,rendered[i],NULL);
    if(acquired&&d.DestroySemaphore)d.DestroySemaphore(device,acquired,NULL);
    if(pool&&d.DestroyCommandPool)d.DestroyCommandPool(device,pool,NULL);
    if(chain&&d.DestroySwapchainKHR)d.DestroySwapchainKHR(device,chain,NULL);
    if(device&&d.DestroyDevice)d.DestroyDevice(device,NULL);
    if(surface&&d.DestroySurfaceKHR)d.DestroySurfaceKHR(instance,surface,NULL);
    if(instance&&d.DestroyInstance)d.DestroyInstance(instance,NULL);
    free(images);free(rendered);
    if(gamepad)SDL_CloseGamepad(gamepad);
    if(window){sc_log("STAGE cleanup: SDL_DestroyWindow\n");SDL_DestroyWindow(window);}
    if(sdl){sc_log("STAGE cleanup: SDL_Quit\n");SDL_Quit();}
    if(screen){sc_log("STAGE cleanup: restore console\n");sc_console(true);}
    sc_log("STAGE cleanup: graphics resources released; result follows\n");
    if(present){
        sc_log("SDL input returned; waiting for native buttons to release before menu polling\n");
        while(appletMainLoop()&&sc_buttons_held()){
            u64 ignored=0;if(!sc_frame(&ignored)){exit_reason="applet_exit";break;}
            svcSleepThread(10000000ull);
        }
    }
    u64 elapsed_ns=armTicksToNs(armGetSystemTick()-attempt_start);
    bool orderly_exit=!strcmp(failure_reason,"user_exit")||!strcmp(failure_reason,"window_close")||!strcmp(failure_reason,"applet_exit");
    const char *result=complete?"PASS":(orderly_exit?"INCOMPLETE":"FAIL");
    const char *reason=complete?(present?"frame_limit":"profile_supported"):failure_reason;
    if(frames==0&&frame_min_ns==UINT64_MAX)frame_min_ns=0;
    write_attempt_result(present,result,reason,frames,attempt_start,elapsed_ns,frame_total_ns,frame_min_ns,frame_max_ns,last_vk_result);
    sc_log("%s result=%s reason=%s; frames=%u elapsed=%.1fms frame_turnaround_avg=%.2fms min=%.2fms max=%.2fms last_vk_result=%d (not Minecraft title verification)\n",
        present?"SDL3 VI presentation":"Snapshot base profile",result,reason,frames,
        (double)elapsed_ns/1000000.0,frames?(double)frame_total_ns/frames/1000000.0:0.0,
        frames?(double)frame_min_ns/1000000.0:0.0,frames?(double)frame_max_ns/1000000.0:0.0,last_vk_result);
    return true;
}
int main(void){
    sc_init("vulkan-present");sc_log("26.4-snapshot-6 Vulkan-only bring-up\nA: exact base feature profile | X: SDL3 VI swapchain / gamepad\nB: diagnostics | +: exit\n");u64 keys;
    while(sc_frame(&keys)){
        if((keys&HidNpadButton_A)&&!run(false))break;
        if((keys&HidNpadButton_X)&&!run(true))break;
        if((keys&HidNpadButton_B)&&sc_chain("switch-diagnostics"))break;
    }
    sc_exit();if(gpu_process_exit_required)svcExitProcess();return 0;
}
