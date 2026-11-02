#include "platform.h"
#include <vulkan/vulkan.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "shaders/triangle_spv.h"

/* NVK is linked directly: no Linux loader, dlopen, or desktop surface. */
extern PFN_vkVoidFunction vkGetInstanceProcAddr(VkInstance,const char *);
#define INSTANCE_FUNCS(X) \
 X(DestroyInstance) X(EnumeratePhysicalDevices) X(GetPhysicalDeviceProperties) \
 X(GetPhysicalDeviceFeatures) X(GetPhysicalDeviceQueueFamilyProperties) \
 X(GetPhysicalDeviceMemoryProperties) X(EnumerateDeviceExtensionProperties) X(CreateDevice) X(GetDeviceProcAddr)
#define DEVICE_FUNCS(X) \
 X(DestroyDevice) X(GetDeviceQueue) X(CreateBuffer) X(DestroyBuffer) \
 X(GetBufferMemoryRequirements) X(AllocateMemory) X(FreeMemory) X(BindBufferMemory) \
 X(MapMemory) X(UnmapMemory) X(InvalidateMappedMemoryRanges) \
 X(CreateCommandPool) X(DestroyCommandPool) X(AllocateCommandBuffers) \
 X(BeginCommandBuffer) X(EndCommandBuffer) X(CmdFillBuffer) X(CmdPipelineBarrier) \
 X(CreateFence) X(DestroyFence) X(QueueSubmit) X(WaitForFences) \
 X(CreateImage) X(DestroyImage) X(GetImageMemoryRequirements) X(BindImageMemory) \
 X(CreateImageView) X(DestroyImageView) X(CreateRenderPass) X(DestroyRenderPass) \
 X(CreateFramebuffer) X(DestroyFramebuffer) X(CreateShaderModule) X(DestroyShaderModule) \
 X(CreatePipelineLayout) X(DestroyPipelineLayout) X(CreateGraphicsPipelines) X(DestroyPipeline) \
 X(CmdBeginRenderPass) X(CmdEndRenderPass) X(CmdBindPipeline) X(CmdDraw) X(CmdCopyImageToBuffer)
#define DECLARE(name) static PFN_vk##name p##name;
INSTANCE_FUNCS(DECLARE)
DEVICE_FUNCS(DECLARE)
#define CHECK(call) do {VkResult r=(call);sc_log("%s -> %d\n",#call,r);if(r!=VK_SUCCESS)goto done;}while(0)

static int memory_type(const VkPhysicalDeviceMemoryProperties *p,uint32_t mask,VkMemoryPropertyFlags flags) {
    for(uint32_t i=0;i<p->memoryTypeCount;i++)
        if((mask&(1u<<i))&&(p->memoryTypes[i].propertyFlags&flags)==flags)return (int)i;
    return -1;
}
/* Returns false on a GPU timeout: exit the application, leave pending objects
 * to process teardown instead of destroying resources still in GPU use. */
static bool test(int mode) {
    VkInstance instance=VK_NULL_HANDLE;VkDevice device=VK_NULL_HANDLE;
    VkBuffer buffer=VK_NULL_HANDLE;VkDeviceMemory buffer_mem=VK_NULL_HANDLE,image_mem=VK_NULL_HANDLE;
    VkCommandPool pool=VK_NULL_HANDLE;VkFence fence=VK_NULL_HANDLE;
    VkImage image=VK_NULL_HANDLE;VkImageView view=VK_NULL_HANDLE;
    VkRenderPass pass=VK_NULL_HANDLE;VkFramebuffer framebuffer=VK_NULL_HANDLE;
    VkShaderModule vs=VK_NULL_HANDLE,fs=VK_NULL_HANDLE;
    VkPipelineLayout layout=VK_NULL_HANDLE;VkPipeline pipeline=VK_NULL_HANDLE;
    void *mapped=NULL;bool passed=false;
    sc_log("\nNVK mode=%d (0=enumerate 1=fill/readback 2=offscreen triangle)\n",mode);
    sc_log("Experimental nonconformant Maxwell driver. No WSI presentation test.\n");
    PFN_vkCreateInstance create=(PFN_vkCreateInstance)vkGetInstanceProcAddr(NULL,"vkCreateInstance");
    PFN_vkEnumerateInstanceExtensionProperties extensions=(PFN_vkEnumerateInstanceExtensionProperties)
        vkGetInstanceProcAddr(NULL,"vkEnumerateInstanceExtensionProperties");
    if(!create||!extensions){sc_log("Missing global Vulkan entrypoints\n");goto done;}
    uint32_t count=0;CHECK(extensions(NULL,&count,NULL));
    VkExtensionProperties *exts=calloc(count?count:1,sizeof(*exts));
    if(!exts){sc_log("Instance extension allocation FAILED\n");goto done;}
    VkResult er=extensions(NULL,&count,exts);
    if(er==VK_SUCCESS)for(uint32_t i=0;i<count;i++)sc_log("Instance extension: %s\n",exts[i].extensionName);
    free(exts);if(er!=VK_SUCCESS)goto done;
    VkApplicationInfo app={.sType=VK_STRUCTURE_TYPE_APPLICATION_INFO,.pApplicationName="Switchcraft",.apiVersion=VK_API_VERSION_1_0};
    VkInstanceCreateInfo ici={.sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,.pApplicationInfo=&app};
    CHECK(create(&ici,NULL,&instance));
#define LOAD_INSTANCE(name) p##name=(PFN_vk##name)vkGetInstanceProcAddr(instance,"vk" #name); if(!p##name){sc_log("Missing vk" #name "\n");goto done;}
    INSTANCE_FUNCS(LOAD_INSTANCE)
    VkPhysicalDevice physicals[16];count=16;
    CHECK(pEnumeratePhysicalDevices(instance,&count,physicals));
    if(!count){sc_log("No physical devices; initialization NOT PASSED\n");goto done;}
    sc_log("Physical devices=%u; GPU tests use first device\n",count);
    for(uint32_t i=0;i<count;i++) {
        VkPhysicalDeviceProperties props;pGetPhysicalDeviceProperties(physicals[i],&props);
        sc_log("GPU %u: %s vendor=%04x device=%04x type=%u API=%u.%u.%u driver=%u\n",i,
            props.deviceName,props.vendorID,props.deviceID,props.deviceType,
            VK_VERSION_MAJOR(props.apiVersion),VK_VERSION_MINOR(props.apiVersion),VK_VERSION_PATCH(props.apiVersion),props.driverVersion);
        sc_log("limits: maxImage2D=%u maxMemoryAllocations=%u maxUniformRange=%u\n",
            props.limits.maxImageDimension2D,props.limits.maxMemoryAllocationCount,props.limits.maxUniformBufferRange);
    }
    VkPhysicalDevice physical=physicals[0];
    VkPhysicalDeviceFeatures features;pGetPhysicalDeviceFeatures(physical,&features);
    sc_log("features: geometry=%u tessellation=%u float64=%u int64=%u sparse=%u\n",
        features.geometryShader,features.tessellationShader,features.shaderFloat64,features.shaderInt64,features.sparseBinding);
    VkPhysicalDeviceMemoryProperties mem;pGetPhysicalDeviceMemoryProperties(physical,&mem);
    for(uint32_t i=0;i<mem.memoryHeapCount;i++)sc_log("Heap %u bytes=%llu flags=0x%x\n",i,(unsigned long long)mem.memoryHeaps[i].size,mem.memoryHeaps[i].flags);
    for(uint32_t i=0;i<mem.memoryTypeCount;i++)sc_log("Memory type %u heap=%u flags=0x%x\n",i,mem.memoryTypes[i].heapIndex,mem.memoryTypes[i].propertyFlags);
    VkQueueFamilyProperties queues[32];count=32;pGetPhysicalDeviceQueueFamilyProperties(physical,&count,queues);
    uint32_t family=UINT32_MAX;
    for(uint32_t i=0;i<count;i++){
        sc_log("Queue family %u count=%u flags=0x%x\n",i,queues[i].queueCount,queues[i].queueFlags);
        if(family==UINT32_MAX&&queues[i].queueCount&&(queues[i].queueFlags&VK_QUEUE_GRAPHICS_BIT))family=i;
    }
    count=0;CHECK(pEnumerateDeviceExtensionProperties(physical,NULL,&count,NULL));
    exts=calloc(count?count:1,sizeof(*exts));if(!exts)goto done;
    er=pEnumerateDeviceExtensionProperties(physical,NULL,&count,exts);
    if(er==VK_SUCCESS)for(uint32_t i=0;i<count;i++)sc_log("Device extension: %s\n",exts[i].extensionName);
    free(exts);if(er!=VK_SUCCESS)goto done;
    if(mode==0){passed=true;goto done;}
    if(family==UINT32_MAX){sc_log("No graphics queue\n");goto done;}
    float priority=1;
    VkDeviceQueueCreateInfo qci={.sType=VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,.queueFamilyIndex=family,.queueCount=1,.pQueuePriorities=&priority};
    VkDeviceCreateInfo dci={.sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,.queueCreateInfoCount=1,.pQueueCreateInfos=&qci};
    CHECK(pCreateDevice(physical,&dci,NULL,&device));
#define LOAD_DEVICE(name) p##name=(PFN_vk##name)pGetDeviceProcAddr(device,"vk" #name); if(!p##name){sc_log("Missing vk" #name "\n");goto done;}
    DEVICE_FUNCS(LOAD_DEVICE)
    VkQueue queue;pGetDeviceQueue(device,family,0,&queue);
    const VkDeviceSize bytes=64*64*4;
    VkBufferCreateInfo bci={.sType=VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,.size=bytes,.usage=VK_BUFFER_USAGE_TRANSFER_DST_BIT,.sharingMode=VK_SHARING_MODE_EXCLUSIVE};
    CHECK(pCreateBuffer(device,&bci,NULL,&buffer));
    VkMemoryRequirements req;pGetBufferMemoryRequirements(device,buffer,&req);
    int type=memory_type(&mem,req.memoryTypeBits,VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT);
    if(type<0){sc_log("No host-visible buffer memory\n");goto done;}
    VkMemoryAllocateInfo mai={.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,.allocationSize=req.size,.memoryTypeIndex=(uint32_t)type};
    CHECK(pAllocateMemory(device,&mai,NULL,&buffer_mem));CHECK(pBindBufferMemory(device,buffer,buffer_mem,0));
    VkCommandPoolCreateInfo pci={.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,.queueFamilyIndex=family};
    CHECK(pCreateCommandPool(device,&pci,NULL,&pool));
    VkCommandBuffer command;
    VkCommandBufferAllocateInfo cai={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,.commandPool=pool,.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY,.commandBufferCount=1};
    CHECK(pAllocateCommandBuffers(device,&cai,&command));
    VkCommandBufferBeginInfo begin={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT};
    CHECK(pBeginCommandBuffer(command,&begin));
    if(mode==1) pCmdFillBuffer(command,buffer,0,bytes,0xcafebabe);
    else {
        VkImageCreateInfo img={.sType=VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,.imageType=VK_IMAGE_TYPE_2D,.format=VK_FORMAT_R8G8B8A8_UNORM,
            .extent={64,64,1},.mipLevels=1,.arrayLayers=1,.samples=VK_SAMPLE_COUNT_1_BIT,.tiling=VK_IMAGE_TILING_OPTIMAL,
            .usage=VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT|VK_IMAGE_USAGE_TRANSFER_SRC_BIT,.sharingMode=VK_SHARING_MODE_EXCLUSIVE,.initialLayout=VK_IMAGE_LAYOUT_UNDEFINED};
        CHECK(pCreateImage(device,&img,NULL,&image));
        pGetImageMemoryRequirements(device,image,&req);type=memory_type(&mem,req.memoryTypeBits,0);
        if(type<0)goto done;
        mai.allocationSize=req.size;mai.memoryTypeIndex=(uint32_t)type;
        CHECK(pAllocateMemory(device,&mai,NULL,&image_mem));CHECK(pBindImageMemory(device,image,image_mem,0));
        VkImageViewCreateInfo vci={.sType=VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,.image=image,.viewType=VK_IMAGE_VIEW_TYPE_2D,
            .format=VK_FORMAT_R8G8B8A8_UNORM,.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1}};
        CHECK(pCreateImageView(device,&vci,NULL,&view));
        VkAttachmentDescription attachment={.format=VK_FORMAT_R8G8B8A8_UNORM,.samples=VK_SAMPLE_COUNT_1_BIT,
            .loadOp=VK_ATTACHMENT_LOAD_OP_CLEAR,.storeOp=VK_ATTACHMENT_STORE_OP_STORE,
            .stencilLoadOp=VK_ATTACHMENT_LOAD_OP_DONT_CARE,.stencilStoreOp=VK_ATTACHMENT_STORE_OP_DONT_CARE,
            .initialLayout=VK_IMAGE_LAYOUT_UNDEFINED,.finalLayout=VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL};
        VkAttachmentReference color={0,VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL};
        VkSubpassDescription sub={.pipelineBindPoint=VK_PIPELINE_BIND_POINT_GRAPHICS,.colorAttachmentCount=1,.pColorAttachments=&color};
        VkSubpassDependency dep={.srcSubpass=0,.dstSubpass=VK_SUBPASS_EXTERNAL,.srcStageMask=VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
            .dstStageMask=VK_PIPELINE_STAGE_TRANSFER_BIT,.srcAccessMask=VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,.dstAccessMask=VK_ACCESS_TRANSFER_READ_BIT};
        VkRenderPassCreateInfo rp={.sType=VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO,.attachmentCount=1,.pAttachments=&attachment,.subpassCount=1,.pSubpasses=&sub,.dependencyCount=1,.pDependencies=&dep};
        CHECK(pCreateRenderPass(device,&rp,NULL,&pass));
        VkFramebufferCreateInfo fb={.sType=VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO,.renderPass=pass,.attachmentCount=1,.pAttachments=&view,.width=64,.height=64,.layers=1};
        CHECK(pCreateFramebuffer(device,&fb,NULL,&framebuffer));
        VkShaderModuleCreateInfo sm={.sType=VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,.codeSize=sizeof(triangle_vert),.pCode=triangle_vert};
        CHECK(pCreateShaderModule(device,&sm,NULL,&vs));sm.codeSize=sizeof(triangle_frag);sm.pCode=triangle_frag;
        CHECK(pCreateShaderModule(device,&sm,NULL,&fs));
        VkPipelineShaderStageCreateInfo stages[2]={{.sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,.stage=VK_SHADER_STAGE_VERTEX_BIT,.module=vs,.pName="main"},
            {.sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,.stage=VK_SHADER_STAGE_FRAGMENT_BIT,.module=fs,.pName="main"}};
        VkPipelineVertexInputStateCreateInfo vertex={.sType=VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
        VkPipelineInputAssemblyStateCreateInfo assembly={.sType=VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO,.topology=VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST};
        VkViewport viewport={0,0,64,64,0,1};VkRect2D rect={{0,0},{64,64}};
        VkPipelineViewportStateCreateInfo vp={.sType=VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO,.viewportCount=1,.pViewports=&viewport,.scissorCount=1,.pScissors=&rect};
        VkPipelineRasterizationStateCreateInfo raster={.sType=VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO,.polygonMode=VK_POLYGON_MODE_FILL,.cullMode=VK_CULL_MODE_NONE,.frontFace=VK_FRONT_FACE_COUNTER_CLOCKWISE,.lineWidth=1};
        VkPipelineMultisampleStateCreateInfo ms={.sType=VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO,.rasterizationSamples=VK_SAMPLE_COUNT_1_BIT};
        VkPipelineColorBlendAttachmentState ba={.colorWriteMask=15};
        VkPipelineColorBlendStateCreateInfo blend={.sType=VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO,.attachmentCount=1,.pAttachments=&ba};
        VkPipelineLayoutCreateInfo pl={.sType=VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        CHECK(pCreatePipelineLayout(device,&pl,NULL,&layout));
        VkGraphicsPipelineCreateInfo gp={.sType=VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO,.stageCount=2,.pStages=stages,
            .pVertexInputState=&vertex,.pInputAssemblyState=&assembly,.pViewportState=&vp,.pRasterizationState=&raster,.pMultisampleState=&ms,
            .pColorBlendState=&blend,.layout=layout,.renderPass=pass,.subpass=0};
        CHECK(pCreateGraphicsPipelines(device,VK_NULL_HANDLE,1,&gp,NULL,&pipeline));
        VkClearValue clear={.color={{0.02f,0.06f,0.15f,1}}};
        VkRenderPassBeginInfo rb={.sType=VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO,.renderPass=pass,.framebuffer=framebuffer,.renderArea=rect,.clearValueCount=1,.pClearValues=&clear};
        pCmdBeginRenderPass(command,&rb,VK_SUBPASS_CONTENTS_INLINE);pCmdBindPipeline(command,VK_PIPELINE_BIND_POINT_GRAPHICS,pipeline);
        pCmdDraw(command,3,1,0,0);pCmdEndRenderPass(command);
        VkBufferImageCopy copy={.imageSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1},.imageExtent={64,64,1}};
        pCmdCopyImageToBuffer(command,image,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,buffer,1,&copy);
    }
    VkBufferMemoryBarrier barrier={.sType=VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER,.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT,.dstAccessMask=VK_ACCESS_HOST_READ_BIT,
        .srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.buffer=buffer,.offset=0,.size=bytes};
    pCmdPipelineBarrier(command,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,0,NULL,1,&barrier,0,NULL);
    CHECK(pEndCommandBuffer(command));
    VkFenceCreateInfo fci={.sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};CHECK(pCreateFence(device,&fci,NULL,&fence));
    VkSubmitInfo submit={.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO,.commandBufferCount=1,.pCommandBuffers=&command};
    CHECK(pQueueSubmit(queue,1,&submit,fence));
    VkResult wait=pWaitForFences(device,1,&fence,VK_TRUE,5000000000ull);
    sc_log("GPU fence -> %d\n",wait);
    if(wait==VK_TIMEOUT){sc_log("GPU timeout; exiting without destroying pending resources\n");return false;}
    if(wait!=VK_SUCCESS)goto done;
    CHECK(pMapMemory(device,buffer_mem,0,VK_WHOLE_SIZE,0,&mapped));
    VkMappedMemoryRange range={.sType=VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE,.memory=buffer_mem,.offset=0,.size=VK_WHOLE_SIZE};
    CHECK(pInvalidateMappedMemoryRanges(device,1,&range));
    if(mode==1) {
        passed=true;uint32_t *words=mapped;
        for(unsigned i=0;i<bytes/4;i++)if(words[i]!=0xcafebabe){sc_log("Mismatch at %u = %08x\n",i,words[i]);passed=false;break;}
        sc_log("4096-word GPU fill/readback: %s\n",passed?"PASS":"FAIL");
    } else {
        unsigned char *pixels=mapped,*center=pixels+(32*64+32)*4;
        passed=center[1]>150&&center[0]<100&&center[2]<130&&pixels[1]<80;
        sc_log("Offscreen triangle center=%u,%u,%u,%u corner=%u,%u,%u: %s\n",center[0],center[1],center[2],center[3],pixels[0],pixels[1],pixels[2],passed?"PASS":"FAIL");
        for(unsigned y=0;y<64;y+=4){for(unsigned x=0;x<64;x+=4)printf("%c",pixels[(y*64+x)*4+1]>150?'#':'.');printf("\n");}
    }
done:
    if(device) {
        if(mapped&&pUnmapMemory)pUnmapMemory(device,buffer_mem);
#define DESTROY(handle,func) if(handle&&p##func)p##func(device,handle,NULL)
        DESTROY(fence,DestroyFence);DESTROY(pool,DestroyCommandPool);DESTROY(pipeline,DestroyPipeline);
        DESTROY(layout,DestroyPipelineLayout);DESTROY(vs,DestroyShaderModule);DESTROY(fs,DestroyShaderModule);
        DESTROY(framebuffer,DestroyFramebuffer);DESTROY(pass,DestroyRenderPass);DESTROY(view,DestroyImageView);
        DESTROY(image,DestroyImage);DESTROY(buffer,DestroyBuffer);DESTROY(image_mem,FreeMemory);DESTROY(buffer_mem,FreeMemory);
        if(pDestroyDevice)pDestroyDevice(device,NULL);
    }
    if(instance&&pDestroyInstance)pDestroyInstance(instance,NULL);
    sc_log("NVK mode %d: %s\n",mode,passed?"PASS":"NOT PASSED");
    return true;
}
int main(void) {
    sc_init("vulkan-test");
    sc_log("A: enumerate GPU | X: fill/readback | Y: offscreen triangle\nB: diagnostics | +: exit\nExperimental NVK; hardware status NOT TESTED\n");
    u64 keys;
    while(sc_frame(&keys)) {
        if((keys&HidNpadButton_A)&&!test(0))break;
        if((keys&HidNpadButton_X)&&!test(1))break;
        if((keys&HidNpadButton_Y)&&!test(2))break;
        if((keys&HidNpadButton_B)&&sc_chain("switch-diagnostics"))break;
    }
    sc_exit();return 0;
}
