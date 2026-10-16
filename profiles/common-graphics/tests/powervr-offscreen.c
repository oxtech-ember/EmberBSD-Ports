/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted).
 * Run the actual consumer with an explicit Vulkan API model. The model checks
 * host ownership and sequencing. It does not execute SPIR-V or prove GPU work.
 */
#include <sys/types.h>
#if defined(__linux__)
#include <sys/sysmacros.h>
#endif
#include <vulkan/vulkan.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks, calls, fail_at, live, pending, completed, mapped;
static unsigned before_barrier, after_barrier, drawn, flushed, image_barrier, copied;
static unsigned mismatch, duplicate, no_queue, no_memory, no_write, bad_word;
static unsigned timeout_wait, partial_pipeline, bad_format, oversized, guard_error;
static unsigned shaders, shader_stage;
static uint8_t cpu[4096], gpu[4096];
#define CHECK(x) do { checks++; if (!(x)) { \
	fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #x); abort(); \
} } while (0)
enum { INSTANCE, DEVICE, IMAGE, IMAGE_MEMORY, VIEW, BUFFER, BUFFER_MEMORY,
    PASS, FRAMEBUFFER, LAYOUT, VERTEX, FRAGMENT, PIPELINE, COMMANDS, FENCE };
#define HANDLE(t, id) ((t)(uintptr_t)((id) + 16))
#define IS(h, id) ((uintptr_t)(h) == (id) + 16U)
static int fail(void) { return ++calls == fail_at; }
static void create(unsigned id) { CHECK(!(live & (1U << id))); live |= 1U << id; }
static void destroy(unsigned id) {
	CHECK(!pending && (live & (1U << id)));
	if (id == BUFFER_MEMORY) CHECK(!mapped && !(live & (1U << BUFFER)));
	if (id == IMAGE_MEMORY) CHECK(!(live & (1U << IMAGE)));
	if (id == DEVICE) CHECK(live == ((1U << INSTANCE) | (1U << DEVICE)));
	if (id == INSTANCE) CHECK(live == (1U << INSTANCE));
	live &= ~(1U << id);
}

VKAPI_ATTR VkResult VKAPI_CALL
vkCreateInstance(const VkInstanceCreateInfo *info, const VkAllocationCallbacks *a,
    VkInstance *out)
{
	CHECK(a == NULL && info->pApplicationInfo->apiVersion == VK_API_VERSION_1_2);
	*out = VK_NULL_HANDLE;
	if (fail()) return VK_ERROR_OUT_OF_HOST_MEMORY;
	create(INSTANCE); *out = HANDLE(VkInstance, INSTANCE); return VK_SUCCESS;
}
VKAPI_ATTR void VKAPI_CALL
vkDestroyInstance(VkInstance h, const VkAllocationCallbacks *a)
{ CHECK(IS(h, INSTANCE) && a == NULL); destroy(INSTANCE); }
VKAPI_ATTR VkResult VKAPI_CALL
vkEnumeratePhysicalDevices(VkInstance h, uint32_t *count, VkPhysicalDevice *out)
{
	CHECK(IS(h, INSTANCE));
	if (fail()) return VK_ERROR_OUT_OF_HOST_MEMORY;
	if (out != NULL) {
		CHECK(*count >= (duplicate ? 2U : 1U));
		out[0] = HANDLE(VkPhysicalDevice, 30);
		if (duplicate) out[1] = HANDLE(VkPhysicalDevice, 31);
	}
	*count = duplicate ? 2 : 1; return VK_SUCCESS;
}
VKAPI_ATTR VkResult VKAPI_CALL
vkEnumerateDeviceExtensionProperties(VkPhysicalDevice h, const char *layer,
    uint32_t *count, VkExtensionProperties *out)
{
	CHECK((IS(h, 30) || IS(h, 31)) && layer == NULL);
	if (fail()) return VK_ERROR_OUT_OF_HOST_MEMORY;
	if (out != NULL) {
		CHECK(*count >= 1);
		memset(out, 0, sizeof(*out));
		strcpy(out->extensionName, mismatch == 6 ? "other" :
		    VK_EXT_PHYSICAL_DEVICE_DRM_EXTENSION_NAME);
	}
	*count = 1; return VK_SUCCESS;
}
VKAPI_ATTR void VKAPI_CALL
vkGetPhysicalDeviceProperties2(VkPhysicalDevice h, VkPhysicalDeviceProperties2 *p)
{
	VkPhysicalDeviceDriverProperties *d = p->pNext;
	VkPhysicalDeviceDrmPropertiesEXT *r = d->pNext;
	CHECK(IS(h, 30) || IS(h, 31));
	p->properties.vendorID = mismatch == 1 ? 0 : 0x1010;
	p->properties.apiVersion = mismatch == 5 ? VK_API_VERSION_1_1 : VK_API_VERSION_1_2;
	strcpy(p->properties.deviceName, "test PowerVR");
	d->driverID = mismatch == 2 ? VK_DRIVER_ID_MESA_LLVMPIPE : VK_DRIVER_ID_IMAGINATION_OPEN_SOURCE_MESA;
	strcpy(d->driverName, "test model");
	r->hasRender = mismatch != 3; r->renderMajor = 180;
	r->renderMinor = mismatch == 4 ? 129 : 128;
}
VKAPI_ATTR void VKAPI_CALL
vkGetPhysicalDeviceQueueFamilyProperties(VkPhysicalDevice h, uint32_t *n,
    VkQueueFamilyProperties *p)
{
	CHECK(IS(h, 30));
	if (p != NULL) {
		CHECK(*n >= 2); memset(p, 0, 2 * sizeof(*p));
		p[0].queueCount = 1; p[0].queueFlags = VK_QUEUE_COMPUTE_BIT;
		p[1].queueCount = 1; p[1].queueFlags = no_queue ? 0 : VK_QUEUE_GRAPHICS_BIT;
	}
	*n = 2;
}
VKAPI_ATTR VkResult VKAPI_CALL
vkCreateDevice(VkPhysicalDevice h, const VkDeviceCreateInfo *p,
    const VkAllocationCallbacks *a, VkDevice *out)
{
	CHECK(IS(h, 30) && a == NULL && p->queueCreateInfoCount == 1);
	CHECK(p->pQueueCreateInfos->queueFamilyIndex == 1 && p->pQueueCreateInfos->queueCount == 1);
	*out = VK_NULL_HANDLE;
	if (fail()) return VK_ERROR_OUT_OF_HOST_MEMORY;
	create(DEVICE); *out = HANDLE(VkDevice, DEVICE); return VK_SUCCESS;
}
VKAPI_ATTR void VKAPI_CALL
vkDestroyDevice(VkDevice h, const VkAllocationCallbacks *a)
{ CHECK(IS(h, DEVICE) && a == NULL); destroy(DEVICE); }
VKAPI_ATTR void VKAPI_CALL
vkGetDeviceQueue(VkDevice h, uint32_t family, uint32_t index, VkQueue *out)
{ CHECK(IS(h, DEVICE) && family == 1 && index == 0); *out = HANDLE(VkQueue, 32); }

VKAPI_ATTR void VKAPI_CALL
vkGetPhysicalDeviceFormatProperties(VkPhysicalDevice p, VkFormat f, VkFormatProperties *v)
{
	CHECK(IS(p, 30) && f == VK_FORMAT_R8G8B8A8_UNORM);
	memset(v, 0, sizeof(*v));
	v->optimalTilingFeatures = VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BIT |
	    (bad_format ? 0 : VK_FORMAT_FEATURE_TRANSFER_SRC_BIT);
}
VKAPI_ATTR VkResult VKAPI_CALL
vkGetPhysicalDeviceImageFormatProperties(VkPhysicalDevice p, VkFormat f,
    VkImageType t, VkImageTiling tiling, VkImageUsageFlags u, VkImageCreateFlags flags,
    VkImageFormatProperties *v)
{
	CHECK(IS(p, 30) && f == VK_FORMAT_R8G8B8A8_UNORM && t == VK_IMAGE_TYPE_2D);
	CHECK(tiling == VK_IMAGE_TILING_OPTIMAL && flags == 0);
	CHECK(u == (VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT));
	if (fail()) return VK_ERROR_FORMAT_NOT_SUPPORTED;
	*v = (VkImageFormatProperties){ .maxExtent = { 16, 16, 1 },
	    .maxMipLevels = 1, .maxArrayLayers = 1, .sampleCounts = VK_SAMPLE_COUNT_1_BIT };
	return VK_SUCCESS;
}
VKAPI_ATTR void VKAPI_CALL
vkGetPhysicalDeviceMemoryProperties(VkPhysicalDevice p, VkPhysicalDeviceMemoryProperties *v)
{
	CHECK(IS(p, 30)); memset(v, 0, sizeof(*v)); v->memoryTypeCount = 2;
	v->memoryTypes[0].propertyFlags = VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT;
	v->memoryTypes[1].propertyFlags = no_memory ? 0 : VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT;
}
VKAPI_ATTR void VKAPI_CALL
vkGetImageMemoryRequirements(VkDevice d, VkImage h, VkMemoryRequirements *v)
{ CHECK(IS(d, DEVICE) && IS(h, IMAGE)); *v = (VkMemoryRequirements){ 4096, 4096, 1 }; }
VKAPI_ATTR void VKAPI_CALL
vkGetBufferMemoryRequirements(VkDevice d, VkBuffer h, VkMemoryRequirements *v)
{
	CHECK(IS(d, DEVICE) && IS(h, BUFFER));
	*v = (VkMemoryRequirements){ oversized ? UINT64_C(32) * 1024 * 1024 : 4096, 4096, 2 };
}
VKAPI_ATTR VkResult VKAPI_CALL
vkAllocateMemory(VkDevice d, const VkMemoryAllocateInfo *p, const VkAllocationCallbacks *a, VkDeviceMemory *h)
{
	unsigned id = p->memoryTypeIndex == 0 ? IMAGE_MEMORY : BUFFER_MEMORY;
	CHECK(IS(d, DEVICE) && a == NULL && p->allocationSize == 4096 && p->memoryTypeIndex <= 1);
	*h = VK_NULL_HANDLE; if (fail()) return VK_ERROR_OUT_OF_DEVICE_MEMORY;
	create(id); *h = HANDLE(VkDeviceMemory, id); return VK_SUCCESS;
}
VKAPI_ATTR void VKAPI_CALL
vkFreeMemory(VkDevice d, VkDeviceMemory h, const VkAllocationCallbacks *a)
{ CHECK(IS(d, DEVICE) && a == NULL); destroy(IS(h, IMAGE_MEMORY) ? IMAGE_MEMORY : BUFFER_MEMORY); }
VKAPI_ATTR VkResult VKAPI_CALL
vkBindImageMemory(VkDevice d, VkImage h, VkDeviceMemory m, VkDeviceSize offset)
{ CHECK(IS(d, DEVICE) && IS(h, IMAGE) && IS(m, IMAGE_MEMORY) && offset == 0); return fail() ? VK_ERROR_OUT_OF_DEVICE_MEMORY : VK_SUCCESS; }
VKAPI_ATTR VkResult VKAPI_CALL
vkBindBufferMemory(VkDevice d, VkBuffer h, VkDeviceMemory m, VkDeviceSize offset)
{ CHECK(IS(d, DEVICE) && IS(h, BUFFER) && IS(m, BUFFER_MEMORY) && offset == 0); return fail() ? VK_ERROR_OUT_OF_DEVICE_MEMORY : VK_SUCCESS; }
VKAPI_ATTR VkResult VKAPI_CALL
vkMapMemory(VkDevice d, VkDeviceMemory m, VkDeviceSize offset, VkDeviceSize n, VkMemoryMapFlags f, void **out)
{
	CHECK(IS(d, DEVICE) && IS(m, BUFFER_MEMORY) && offset == 0 && n == VK_WHOLE_SIZE && f == 0);
	if (fail()) return VK_ERROR_MEMORY_MAP_FAILED;
	mapped = 1; *out = cpu; return VK_SUCCESS;
}
VKAPI_ATTR void VKAPI_CALL
vkUnmapMemory(VkDevice d, VkDeviceMemory m)
{ CHECK(IS(d, DEVICE) && IS(m, BUFFER_MEMORY) && mapped && !pending); mapped = 0; }
static void memory_range(VkDevice d, uint32_t n, const VkMappedMemoryRange *r)
{ CHECK(IS(d, DEVICE) && n == 1 && mapped && IS(r->memory, BUFFER_MEMORY) && r->offset == 0 && r->size == VK_WHOLE_SIZE); }
VKAPI_ATTR VkResult VKAPI_CALL
vkFlushMappedMemoryRanges(VkDevice d, uint32_t n, const VkMappedMemoryRange *r)
{
	memory_range(d, n, r); if (fail()) return VK_ERROR_DEVICE_LOST;
	CHECK(cpu[0] == 0xa5 && cpu[4095] == 0xa5); memcpy(gpu, cpu, sizeof(cpu)); flushed = 1; return VK_SUCCESS;
}
VKAPI_ATTR VkResult VKAPI_CALL
vkInvalidateMappedMemoryRanges(VkDevice d, uint32_t n, const VkMappedMemoryRange *r)
{
	memory_range(d, n, r); CHECK(!pending && completed);
	if (fail()) return VK_ERROR_DEVICE_LOST;
	memcpy(cpu, gpu, sizeof(cpu)); return VK_SUCCESS;
}

static void validate(unsigned id, const void *v)
{
	switch (id) {
	case IMAGE: {
		const VkImageCreateInfo *p = v;
		CHECK(p->extent.width == 16 && p->extent.height == 16 && p->extent.depth == 1);
		CHECK(p->format == VK_FORMAT_R8G8B8A8_UNORM && p->tiling == VK_IMAGE_TILING_OPTIMAL);
		CHECK(p->initialLayout == VK_IMAGE_LAYOUT_UNDEFINED && p->mipLevels == 1 && p->arrayLayers == 1); break;
	}
	case VIEW: { const VkImageViewCreateInfo *p = v; CHECK(IS(p->image, IMAGE) && p->viewType == VK_IMAGE_VIEW_TYPE_2D); break; }
	case BUFFER: { const VkBufferCreateInfo *p = v; CHECK(p->size == 1568 && p->usage == VK_BUFFER_USAGE_TRANSFER_DST_BIT); break; }
	case PASS: {
		const VkRenderPassCreateInfo *p = v;
		CHECK(p->attachmentCount == 1 && p->subpassCount == 1);
		CHECK(p->pAttachments->loadOp == VK_ATTACHMENT_LOAD_OP_CLEAR && p->pAttachments->storeOp == VK_ATTACHMENT_STORE_OP_STORE);
		CHECK(p->pAttachments->initialLayout == VK_IMAGE_LAYOUT_UNDEFINED && p->pAttachments->finalLayout == VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL); break;
	}
	case FRAMEBUFFER: { const VkFramebufferCreateInfo *p = v; CHECK(IS(p->renderPass, PASS) && p->width == 16 && p->height == 16 && p->layers == 1 && IS(*p->pAttachments, VIEW)); break; }
	case LAYOUT: { const VkPipelineLayoutCreateInfo *p = v; CHECK(p->setLayoutCount == 0 && p->pushConstantRangeCount == 0); break; }
	case COMMANDS: { const VkCommandPoolCreateInfo *p = v; CHECK(p->queueFamilyIndex == 1); break; }
	case FENCE: { const VkFenceCreateInfo *p = v; CHECK(p->flags == 0); break; }
	default: CHECK(0);
	}
}
#define CREATE(Name, ID) \
VKAPI_ATTR VkResult VKAPI_CALL vkCreate##Name(VkDevice d, const Vk##Name##CreateInfo *p, const VkAllocationCallbacks *a, Vk##Name *h) \
{ CHECK(IS(d, DEVICE) && a == NULL); validate(ID, p); *h = VK_NULL_HANDLE; if (fail()) return VK_ERROR_OUT_OF_HOST_MEMORY; create(ID); *h = HANDLE(Vk##Name, ID); return VK_SUCCESS; } \
VKAPI_ATTR void VKAPI_CALL vkDestroy##Name(VkDevice d, Vk##Name h, const VkAllocationCallbacks *a) \
{ CHECK(IS(d, DEVICE) && IS(h, ID) && a == NULL); destroy(ID); }
CREATE(Image, IMAGE)
CREATE(ImageView, VIEW)
CREATE(Buffer, BUFFER)
CREATE(RenderPass, PASS)
CREATE(Framebuffer, FRAMEBUFFER)
CREATE(PipelineLayout, LAYOUT)
CREATE(CommandPool, COMMANDS)
CREATE(Fence, FENCE)
VKAPI_ATTR VkResult VKAPI_CALL
vkCreateShaderModule(VkDevice d, const VkShaderModuleCreateInfo *p, const VkAllocationCallbacks *a, VkShaderModule *h)
{
	unsigned id = shaders == 0 ? VERTEX : FRAGMENT;
	CHECK(IS(d, DEVICE) && a == NULL && p->codeSize >= 20 && p->codeSize % 4 == 0 && p->pCode[0] == 0x07230203);
	*h = VK_NULL_HANDLE; if (fail()) return VK_ERROR_OUT_OF_HOST_MEMORY;
	create(id); shaders++; *h = HANDLE(VkShaderModule, id); return VK_SUCCESS;
}
VKAPI_ATTR void VKAPI_CALL
vkDestroyShaderModule(VkDevice d, VkShaderModule h, const VkAllocationCallbacks *a)
{ CHECK(IS(d, DEVICE) && a == NULL); destroy(IS(h, VERTEX) ? VERTEX : FRAGMENT); }
VKAPI_ATTR VkResult VKAPI_CALL
vkCreateGraphicsPipelines(VkDevice d, VkPipelineCache cache, uint32_t n, const VkGraphicsPipelineCreateInfo *p, const VkAllocationCallbacks *a, VkPipeline *h)
{
	CHECK(IS(d, DEVICE) && cache == VK_NULL_HANDLE && n == 1 && a == NULL);
	CHECK(p->stageCount == 2 && p->pStages[0].stage == VK_SHADER_STAGE_VERTEX_BIT && p->pStages[1].stage == VK_SHADER_STAGE_FRAGMENT_BIT);
	CHECK(p->pInputAssemblyState->topology == VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST && !p->pInputAssemblyState->primitiveRestartEnable);
	CHECK(p->pVertexInputState->vertexBindingDescriptionCount == 0 && p->pRasterizationState->cullMode == VK_CULL_MODE_NONE);
	CHECK(p->pViewportState->pViewports->width == 16 && p->pViewportState->pViewports->height == 16);
	CHECK(p->pColorBlendState->pAttachments->colorWriteMask == 15 && !p->pColorBlendState->pAttachments->blendEnable);
	CHECK(IS(p->renderPass, PASS) && IS(p->layout, LAYOUT) && p->pMultisampleState->rasterizationSamples == VK_SAMPLE_COUNT_1_BIT);
	*h = VK_NULL_HANDLE; if (fail()) return VK_ERROR_OUT_OF_HOST_MEMORY;
	create(PIPELINE); *h = HANDLE(VkPipeline, PIPELINE);
	return partial_pipeline ? VK_ERROR_OUT_OF_HOST_MEMORY : VK_SUCCESS;
}
VKAPI_ATTR void VKAPI_CALL
vkDestroyPipeline(VkDevice d, VkPipeline h, const VkAllocationCallbacks *a)
{ CHECK(IS(d, DEVICE) && IS(h, PIPELINE) && a == NULL); destroy(PIPELINE); }
VKAPI_ATTR VkResult VKAPI_CALL
vkAllocateCommandBuffers(VkDevice d, const VkCommandBufferAllocateInfo *p, VkCommandBuffer *c)
{ CHECK(IS(d, DEVICE) && IS(p->commandPool, COMMANDS) && p->commandBufferCount == 1); if (fail()) return VK_ERROR_OUT_OF_HOST_MEMORY; *c = HANDLE(VkCommandBuffer, 33); return VK_SUCCESS; }
VKAPI_ATTR VkResult VKAPI_CALL
vkBeginCommandBuffer(VkCommandBuffer c, const VkCommandBufferBeginInfo *p)
{ CHECK(IS(c, 33) && p->flags == VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT); return fail() ? VK_ERROR_OUT_OF_HOST_MEMORY : VK_SUCCESS; }
VKAPI_ATTR VkResult VKAPI_CALL
vkEndCommandBuffer(VkCommandBuffer c)
{ CHECK(IS(c, 33)); return fail() ? VK_ERROR_OUT_OF_HOST_MEMORY : VK_SUCCESS; }
VKAPI_ATTR void VKAPI_CALL
vkCmdPipelineBarrier(VkCommandBuffer c, VkPipelineStageFlags src, VkPipelineStageFlags dst, VkDependencyFlags flags, uint32_t nm, const VkMemoryBarrier *m, uint32_t nb, const VkBufferMemoryBarrier *b, uint32_t ni, const VkImageMemoryBarrier *i)
{
	CHECK(IS(c, 33) && flags == 0 && nm == 0 && m == NULL);
	if (ni) {
		CHECK(nb == 0 && b == NULL && ni == 1 && IS(i->image, IMAGE));
		CHECK(src == VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT && dst == VK_PIPELINE_STAGE_TRANSFER_BIT);
		CHECK(i->srcAccessMask == VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT && i->dstAccessMask == VK_ACCESS_TRANSFER_READ_BIT);
		CHECK(i->oldLayout == VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL && i->newLayout == VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL);
		CHECK(i->srcQueueFamilyIndex == VK_QUEUE_FAMILY_IGNORED && i->dstQueueFamilyIndex == VK_QUEUE_FAMILY_IGNORED);
		image_barrier++; return;
	}
	CHECK(i == NULL && nb == 1 && IS(b->buffer, BUFFER) && b->offset == 0 && b->size == VK_WHOLE_SIZE);
	CHECK(b->srcQueueFamilyIndex == VK_QUEUE_FAMILY_IGNORED && b->dstQueueFamilyIndex == VK_QUEUE_FAMILY_IGNORED);
	if (src == VK_PIPELINE_STAGE_HOST_BIT) {
		CHECK(dst == VK_PIPELINE_STAGE_TRANSFER_BIT && b->srcAccessMask == VK_ACCESS_HOST_WRITE_BIT && b->dstAccessMask == VK_ACCESS_TRANSFER_WRITE_BIT); before_barrier++;
	} else {
		CHECK(src == VK_PIPELINE_STAGE_TRANSFER_BIT && dst == VK_PIPELINE_STAGE_HOST_BIT);
		CHECK(b->srcAccessMask == VK_ACCESS_TRANSFER_WRITE_BIT && b->dstAccessMask == VK_ACCESS_HOST_READ_BIT); after_barrier++;
	}
}
VKAPI_ATTR void VKAPI_CALL
vkCmdBeginRenderPass(VkCommandBuffer c, const VkRenderPassBeginInfo *p, VkSubpassContents contents)
{
	CHECK(IS(c, 33) && IS(p->renderPass, PASS) && IS(p->framebuffer, FRAMEBUFFER) && contents == VK_SUBPASS_CONTENTS_INLINE);
	CHECK(p->clearValueCount == 1 && p->pClearValues->color.float32[0] == 1 && p->pClearValues->color.float32[1] == 0 && p->pClearValues->color.float32[2] == 0 && p->pClearValues->color.float32[3] == 1);
}
VKAPI_ATTR void VKAPI_CALL
vkCmdBindPipeline(VkCommandBuffer c, VkPipelineBindPoint bind, VkPipeline p)
{ CHECK(IS(c, 33) && bind == VK_PIPELINE_BIND_POINT_GRAPHICS && IS(p, PIPELINE)); shader_stage = 1; }
VKAPI_ATTR void VKAPI_CALL
vkCmdDraw(VkCommandBuffer c, uint32_t vertices, uint32_t instances, uint32_t first, uint32_t first_instance)
{ CHECK(IS(c, 33) && vertices == 3 && instances == 1 && first == 0 && first_instance == 0 && shader_stage); drawn++; }
VKAPI_ATTR void VKAPI_CALL
vkCmdEndRenderPass(VkCommandBuffer c) { CHECK(IS(c, 33) && drawn == 1); }
VKAPI_ATTR void VKAPI_CALL
vkCmdCopyImageToBuffer(VkCommandBuffer c, VkImage image, VkImageLayout layout, VkBuffer b, uint32_t n, const VkBufferImageCopy *p)
{
	CHECK(IS(c, 33) && IS(image, IMAGE) && layout == VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL && IS(b, BUFFER) && n == 1);
	CHECK(image_barrier == 1 && p->bufferOffset == 64 && p->bufferRowLength == 20 && p->bufferImageHeight == 18);
	CHECK(p->imageExtent.width == 16 && p->imageExtent.height == 16 && p->imageExtent.depth == 1 && p->imageSubresource.layerCount == 1);
	copied++;
}
VKAPI_ATTR VkResult VKAPI_CALL
vkQueueSubmit(VkQueue q, uint32_t n, const VkSubmitInfo *s, VkFence f)
{
	static const unsigned left[16] = { 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8 };
	unsigned y, x, offset;
	CHECK(IS(q, 32) && n == 1 && IS(f, FENCE) && s->commandBufferCount == 1);
	CHECK(flushed && before_barrier == 1 && image_barrier == 1 && after_barrier == 1 && drawn == 1 && copied == 1);
	pending = 1;
	if (fail()) return VK_ERROR_DEVICE_LOST;
	if (!no_write) {
		for (y = 0; y < 16; y++) for (x = 0; x < 16; x++) {
			bool green = x >= left[y] && x < 16 - left[y];
			offset = 64 + y * 80 + x * 4;
			gpu[offset] = green ? 0 : 255; gpu[offset + 1] = green ? 255 : 0;
			gpu[offset + 2] = 0; gpu[offset + 3] = 255;
		}
	}
	if (bad_word) gpu[64 + 8 * 80 + 8 * 4] ^= 1;
	if (guard_error) gpu[guard_error == 1 ? 0 : guard_error == 2 ? 128 : 1504] ^= 1;
	return VK_SUCCESS;
}
VKAPI_ATTR VkResult VKAPI_CALL
vkWaitForFences(VkDevice d, uint32_t n, const VkFence *f, VkBool32 all, uint64_t ns)
{
	CHECK(IS(d, DEVICE) && n == 1 && IS(*f, FENCE) && all && ns == UINT64_C(10000000000) && pending);
	if (fail()) return VK_ERROR_DEVICE_LOST;
	if (timeout_wait) return VK_TIMEOUT;
	pending = 0; completed = 1; return VK_SUCCESS;
}
#define main consumer_main
#include <powervr-offscreen.c>
#undef main
static void reset(void)
{
	calls = fail_at = live = pending = completed = mapped = 0;
	before_barrier = after_barrier = drawn = flushed = image_barrier = copied = 0;
	mismatch = duplicate = no_queue = no_memory = no_write = bad_word = 0;
	timeout_wait = partial_pipeline = bad_format = oversized = guard_error = 0;
	shaders = shader_stage = 0; memset(cpu, 0, sizeof(cpu)); memset(gpu, 0, sizeof(gpu));
}
static void run(int expected)
{
	int status = run_offscreen(makedev(180, 128));
	CHECK(status == expected);
	if (status == PENDING_EXIT) CHECK(pending && live && mapped);
	else CHECK(live == 0 && !mapped && !pending);
}
int main(void)
{
	unsigned i, total;
	reset(); run(0); total = calls;
	for (i = 1; i <= total; i++) {
		reset(); fail_at = i;
		int result = run_offscreen(makedev(180, 128));
		CHECK(result != 0);
		if (result == PENDING_EXIT) CHECK(pending && live && mapped);
		else CHECK(live == 0 && !mapped && !pending);
	}
	for (i = 1; i <= 6; i++) { reset(); mismatch = i; run(1); }
	reset(); duplicate = 1; run(1);
	reset(); no_queue = 1; run(1);
	reset(); no_memory = 1; run(1);
	reset(); bad_format = 1; run(1);
	reset(); oversized = 1; run(1);
	reset(); no_write = 1; run(1);
	reset(); bad_word = 1; run(1);
	reset(); partial_pipeline = 1; run(1);
	for (i = 1; i <= 3; i++) { reset(); guard_error = i; run(1); }
	reset(); timeout_wait = 1; run(PENDING_EXIT);
	printf("offscreen consumer: %u checks, %u API fault positions passed\n", checks, total);
	return 0;
}
