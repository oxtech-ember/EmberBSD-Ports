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
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks, calls, fail_at, live, pending, completed, mapped;
static unsigned before_barrier, after_barrier, dispatched, flushed, bound;
static unsigned mismatch, duplicate, no_queue, no_memory, no_write, bad_word;
static unsigned timeout_wait, partial_pipeline;
static uint32_t cpu[1024], gpu[1024];
#define CHECK(x) do { checks++; if (!(x)) { \
	fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #x); abort(); \
} } while (0)
enum { INSTANCE, DEVICE, BUFFER, MEMORY, SET_LAYOUT, LAYOUT, SHADER,
    PIPELINE, DESCRIPTORS, COMMANDS, FENCE };
#define HANDLE(t, id) ((t)(uintptr_t)((id) + 16))
#define IS(h, id) ((uintptr_t)(h) == (id) + 16U)
static int fail(void) { return ++calls == fail_at; }
static void create(unsigned id) { CHECK(!(live & (1U << id))); live |= 1U << id; }
static void destroy(unsigned id) {
	CHECK(!pending && (live & (1U << id)));
	if (id == MEMORY) CHECK(!mapped && !(live & (1U << BUFFER)));
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
		p[0].queueCount = 1; p[0].queueFlags = VK_QUEUE_GRAPHICS_BIT;
		p[1].queueCount = 1; p[1].queueFlags = no_queue ? 0 : VK_QUEUE_COMPUTE_BIT;
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

static void validate(unsigned id, const void *info)
{
	switch (id) {
	case BUFFER: {
		const VkBufferCreateInfo *p = info;
		CHECK(p->size == 64 && p->usage == VK_BUFFER_USAGE_STORAGE_BUFFER_BIT && p->sharingMode == VK_SHARING_MODE_EXCLUSIVE); break;
	}
	case SET_LAYOUT: {
		const VkDescriptorSetLayoutCreateInfo *p = info;
		CHECK(p->bindingCount == 1 && p->pBindings->binding == 0 && p->pBindings->descriptorCount == 1);
		CHECK(p->pBindings->descriptorType == VK_DESCRIPTOR_TYPE_STORAGE_BUFFER && p->pBindings->stageFlags == VK_SHADER_STAGE_COMPUTE_BIT); break;
	}
	case LAYOUT: {
		const VkPipelineLayoutCreateInfo *p = info;
		CHECK(p->setLayoutCount == 1 && IS(*p->pSetLayouts, SET_LAYOUT)); break;
	}
	case SHADER: {
		const VkShaderModuleCreateInfo *p = info;
		CHECK(p->codeSize >= 20 && p->codeSize % 4 == 0 && p->pCode[0] == 0x07230203);
		CHECK(p->pCode[1] == 0x00010500); break;
	}
	case DESCRIPTORS: {
		const VkDescriptorPoolCreateInfo *p = info;
		CHECK(p->maxSets == 1 && p->poolSizeCount == 1 && p->pPoolSizes->type == VK_DESCRIPTOR_TYPE_STORAGE_BUFFER && p->pPoolSizes->descriptorCount == 1); break;
	}
	case COMMANDS: {
		const VkCommandPoolCreateInfo *p = info;
		CHECK(p->queueFamilyIndex == 1); break;
	}
	case FENCE: {
		const VkFenceCreateInfo *p = info;
		CHECK(p->flags == 0); break;
	}
	default: CHECK(0);
	}
}
#define CREATE(fn, type, infotype, id) \
VKAPI_ATTR VkResult VKAPI_CALL fn(VkDevice d, const infotype *p, \
    const VkAllocationCallbacks *a, type *out) { \
	CHECK(IS(d, DEVICE) && a == NULL); validate(id, p); *out = VK_NULL_HANDLE; \
	if (fail()) return VK_ERROR_OUT_OF_HOST_MEMORY; \
	create(id); *out = HANDLE(type, id); return VK_SUCCESS; \
}
#define DESTROY(fn, type, id) \
VKAPI_ATTR void VKAPI_CALL fn(VkDevice d, type h, const VkAllocationCallbacks *a) { \
	CHECK(IS(d, DEVICE) && IS(h, id) && a == NULL); destroy(id); \
}
CREATE(vkCreateBuffer, VkBuffer, VkBufferCreateInfo, BUFFER)
CREATE(vkCreateDescriptorSetLayout, VkDescriptorSetLayout, VkDescriptorSetLayoutCreateInfo, SET_LAYOUT)
CREATE(vkCreatePipelineLayout, VkPipelineLayout, VkPipelineLayoutCreateInfo, LAYOUT)
CREATE(vkCreateShaderModule, VkShaderModule, VkShaderModuleCreateInfo, SHADER)
CREATE(vkCreateDescriptorPool, VkDescriptorPool, VkDescriptorPoolCreateInfo, DESCRIPTORS)
CREATE(vkCreateCommandPool, VkCommandPool, VkCommandPoolCreateInfo, COMMANDS)
CREATE(vkCreateFence, VkFence, VkFenceCreateInfo, FENCE)
DESTROY(vkDestroyBuffer, VkBuffer, BUFFER)
DESTROY(vkDestroyDescriptorSetLayout, VkDescriptorSetLayout, SET_LAYOUT)
DESTROY(vkDestroyPipelineLayout, VkPipelineLayout, LAYOUT)
DESTROY(vkDestroyShaderModule, VkShaderModule, SHADER)
DESTROY(vkDestroyPipeline, VkPipeline, PIPELINE)
DESTROY(vkDestroyDescriptorPool, VkDescriptorPool, DESCRIPTORS)
DESTROY(vkDestroyCommandPool, VkCommandPool, COMMANDS)
DESTROY(vkDestroyFence, VkFence, FENCE)
DESTROY(vkFreeMemory, VkDeviceMemory, MEMORY)
VKAPI_ATTR void VKAPI_CALL
vkGetBufferMemoryRequirements(VkDevice d, VkBuffer b, VkMemoryRequirements *r)
{ CHECK(IS(d, DEVICE) && IS(b, BUFFER)); r->size = sizeof(cpu); r->alignment = 64; r->memoryTypeBits = 2; }
VKAPI_ATTR void VKAPI_CALL
vkGetPhysicalDeviceMemoryProperties(VkPhysicalDevice h, VkPhysicalDeviceMemoryProperties *p)
{
	CHECK(IS(h, 30)); memset(p, 0, sizeof(*p)); p->memoryTypeCount = 2;
	p->memoryTypes[0].propertyFlags = VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT;
	p->memoryTypes[1].propertyFlags = no_memory ? 0 : VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT;
}
VKAPI_ATTR VkResult VKAPI_CALL
vkAllocateMemory(VkDevice d, const VkMemoryAllocateInfo *p, const VkAllocationCallbacks *a, VkDeviceMemory *out)
{
	CHECK(IS(d, DEVICE) && a == NULL && p->allocationSize == sizeof(cpu) && p->memoryTypeIndex == 1);
	*out = VK_NULL_HANDLE; if (fail()) return VK_ERROR_OUT_OF_HOST_MEMORY;
	create(MEMORY); *out = HANDLE(VkDeviceMemory, MEMORY); return VK_SUCCESS;
}
VKAPI_ATTR VkResult VKAPI_CALL
vkBindBufferMemory(VkDevice d, VkBuffer b, VkDeviceMemory m, VkDeviceSize o)
{
	CHECK(IS(d, DEVICE) && IS(b, BUFFER) && IS(m, MEMORY) && o == 0);
	if (fail())
		return VK_ERROR_OUT_OF_HOST_MEMORY;
	bound = 1;
	return VK_SUCCESS;
}
VKAPI_ATTR VkResult VKAPI_CALL
vkMapMemory(VkDevice d, VkDeviceMemory m, VkDeviceSize offset, VkDeviceSize size,
    VkMemoryMapFlags flags, void **out)
{
	CHECK(IS(d, DEVICE) && IS(m, MEMORY) && offset == 0 && size == VK_WHOLE_SIZE && flags == 0 && bound);
	if (fail()) return VK_ERROR_OUT_OF_HOST_MEMORY;
	mapped = 1; *out = cpu; return VK_SUCCESS;
}
VKAPI_ATTR void VKAPI_CALL
vkUnmapMemory(VkDevice d, VkDeviceMemory m)
{ CHECK(IS(d, DEVICE) && IS(m, MEMORY) && mapped && !pending); mapped = 0; }
static void range_check(VkDevice d, uint32_t n, const VkMappedMemoryRange *p)
{ CHECK(IS(d, DEVICE) && n == 1 && IS(p->memory, MEMORY) && p->offset == 0 && p->size == VK_WHOLE_SIZE && mapped); }
VKAPI_ATTR VkResult VKAPI_CALL
vkFlushMappedMemoryRanges(VkDevice d, uint32_t n, const VkMappedMemoryRange *p)
{
	range_check(d, n, p); if (fail()) return VK_ERROR_OUT_OF_HOST_MEMORY;
	for (unsigned i = 0; i < 16; i++) CHECK(cpu[i] == 0xdeadbeefU);
	memcpy(gpu, cpu, sizeof(gpu)); flushed = 1; return VK_SUCCESS;
}
VKAPI_ATTR VkResult VKAPI_CALL
vkInvalidateMappedMemoryRanges(VkDevice d, uint32_t n, const VkMappedMemoryRange *p)
{
	range_check(d, n, p); CHECK(completed && !pending && after_barrier);
	if (fail()) return VK_ERROR_OUT_OF_HOST_MEMORY;
	memcpy(cpu, gpu, sizeof(cpu)); return VK_SUCCESS;
}
VKAPI_ATTR VkResult VKAPI_CALL
vkCreateComputePipelines(VkDevice d, VkPipelineCache cache, uint32_t n,
    const VkComputePipelineCreateInfo *p, const VkAllocationCallbacks *a, VkPipeline *out)
{
	CHECK(IS(d, DEVICE) && cache == VK_NULL_HANDLE && n == 1 && a == NULL);
	CHECK(p->stage.stage == VK_SHADER_STAGE_COMPUTE_BIT && IS(p->stage.module, SHADER) && strcmp(p->stage.pName, "main") == 0 && IS(p->layout, LAYOUT));
	*out = VK_NULL_HANDLE;
	if (fail()) return VK_ERROR_OUT_OF_HOST_MEMORY;
	create(PIPELINE); *out = HANDLE(VkPipeline, PIPELINE);
	return partial_pipeline ? VK_ERROR_OUT_OF_HOST_MEMORY : VK_SUCCESS;
}
VKAPI_ATTR VkResult VKAPI_CALL
vkAllocateDescriptorSets(VkDevice d, const VkDescriptorSetAllocateInfo *p, VkDescriptorSet *out)
{
	CHECK(IS(d, DEVICE) && IS(p->descriptorPool, DESCRIPTORS) && p->descriptorSetCount == 1 && IS(*p->pSetLayouts, SET_LAYOUT));
	if (fail())
		return VK_ERROR_OUT_OF_HOST_MEMORY;
	*out = HANDLE(VkDescriptorSet, 33);
	return VK_SUCCESS;
}
VKAPI_ATTR void VKAPI_CALL
vkUpdateDescriptorSets(VkDevice d, uint32_t n, const VkWriteDescriptorSet *p,
    uint32_t copies, const VkCopyDescriptorSet *copy)
{
	CHECK(IS(d, DEVICE) && n == 1 && copies == 0 && copy == NULL && IS(p->dstSet, 33));
	CHECK(p->dstBinding == 0 && p->descriptorCount == 1 && p->descriptorType == VK_DESCRIPTOR_TYPE_STORAGE_BUFFER);
	CHECK(IS(p->pBufferInfo->buffer, BUFFER) && p->pBufferInfo->offset == 0 && p->pBufferInfo->range == 64);
}
VKAPI_ATTR VkResult VKAPI_CALL
vkAllocateCommandBuffers(VkDevice d, const VkCommandBufferAllocateInfo *p, VkCommandBuffer *out)
{
	CHECK(IS(d, DEVICE) && IS(p->commandPool, COMMANDS) && p->commandBufferCount == 1 && p->level == VK_COMMAND_BUFFER_LEVEL_PRIMARY);
	if (fail())
		return VK_ERROR_OUT_OF_HOST_MEMORY;
	*out = HANDLE(VkCommandBuffer, 34);
	return VK_SUCCESS;
}
VKAPI_ATTR VkResult VKAPI_CALL
vkBeginCommandBuffer(VkCommandBuffer c, const VkCommandBufferBeginInfo *p)
{ CHECK(IS(c, 34) && p->flags == VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT); return fail() ? VK_ERROR_OUT_OF_HOST_MEMORY : VK_SUCCESS; }
VKAPI_ATTR void VKAPI_CALL
vkCmdPipelineBarrier(VkCommandBuffer c, VkPipelineStageFlags src, VkPipelineStageFlags dst,
    VkDependencyFlags flags, uint32_t nmem, const VkMemoryBarrier *mem,
    uint32_t nb, const VkBufferMemoryBarrier *b, uint32_t ni, const VkImageMemoryBarrier *image)
{
	CHECK(IS(c, 34) && flags == 0 && nmem == 0 && mem == NULL && nb == 1 && ni == 0 && image == NULL);
	CHECK(IS(b->buffer, BUFFER) && b->offset == 0 && b->size == 64 && b->srcQueueFamilyIndex == VK_QUEUE_FAMILY_IGNORED && b->dstQueueFamilyIndex == VK_QUEUE_FAMILY_IGNORED);
	if (!dispatched) {
		CHECK(src == VK_PIPELINE_STAGE_HOST_BIT && dst == VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT && b->srcAccessMask == VK_ACCESS_HOST_WRITE_BIT && b->dstAccessMask == VK_ACCESS_SHADER_WRITE_BIT);
		before_barrier = 1;
	} else {
		CHECK(src == VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT && dst == VK_PIPELINE_STAGE_HOST_BIT && b->srcAccessMask == VK_ACCESS_SHADER_WRITE_BIT && b->dstAccessMask == VK_ACCESS_HOST_READ_BIT);
		after_barrier = 1;
	}
}
VKAPI_ATTR void VKAPI_CALL
vkCmdBindPipeline(VkCommandBuffer c, VkPipelineBindPoint point, VkPipeline p)
{ CHECK(IS(c, 34) && point == VK_PIPELINE_BIND_POINT_COMPUTE && IS(p, PIPELINE)); }
VKAPI_ATTR void VKAPI_CALL
vkCmdBindDescriptorSets(VkCommandBuffer c, VkPipelineBindPoint point, VkPipelineLayout layout,
    uint32_t first, uint32_t n, const VkDescriptorSet *p, uint32_t ndyn, const uint32_t *dyn)
{ CHECK(IS(c, 34) && point == VK_PIPELINE_BIND_POINT_COMPUTE && IS(layout, LAYOUT) && first == 0 && n == 1 && IS(*p, 33) && ndyn == 0 && dyn == NULL); }
VKAPI_ATTR void VKAPI_CALL
vkCmdDispatch(VkCommandBuffer c, uint32_t x, uint32_t y, uint32_t z)
{ CHECK(IS(c, 34) && x == 16 && y == 1 && z == 1 && before_barrier && flushed); dispatched = 1; }
VKAPI_ATTR VkResult VKAPI_CALL
vkEndCommandBuffer(VkCommandBuffer c)
{ CHECK(IS(c, 34) && dispatched && after_barrier); return fail() ? VK_ERROR_OUT_OF_HOST_MEMORY : VK_SUCCESS; }
VKAPI_ATTR VkResult VKAPI_CALL
vkQueueSubmit(VkQueue q, uint32_t n, const VkSubmitInfo *p, VkFence f)
{
	CHECK(IS(q, 32) && n == 1 && IS(f, FENCE) && p->commandBufferCount == 1 && IS(*p->pCommandBuffers, 34));
	CHECK(p->waitSemaphoreCount == 0 && p->signalSemaphoreCount == 0 && dispatched && after_barrier);
	pending = 1; return fail() ? VK_ERROR_DEVICE_LOST : VK_SUCCESS;
}
VKAPI_ATTR VkResult VKAPI_CALL
vkWaitForFences(VkDevice d, uint32_t n, const VkFence *p, VkBool32 all, uint64_t timeout)
{
	CHECK(IS(d, DEVICE) && n == 1 && IS(*p, FENCE) && all == VK_TRUE && timeout == 10000000000ULL && pending);
	if (fail()) return VK_ERROR_DEVICE_LOST;
	if (timeout_wait) return VK_TIMEOUT;
	if (!no_write) for (unsigned i = 0; i < 16; i++) gpu[i] = 0x13579bdfU ^ i;
	if (bad_word) gpu[15] ^= 1;
	pending = 0; completed = 1; return VK_SUCCESS;
}

#define main compute_main
#include <powervr-compute.c>
#undef main

static void reset(void)
{
	calls = fail_at = live = pending = completed = mapped = 0;
	before_barrier = after_barrier = dispatched = flushed = bound = 0;
	mismatch = duplicate = no_queue = no_memory = no_write = bad_word = 0;
	timeout_wait = partial_pipeline = 0;
	memset(cpu, 0, sizeof(cpu)); memset(gpu, 0, sizeof(gpu));
}
static void ordinary(int expected)
{ CHECK(run_compute(makedev(180, 128)) == expected); CHECK(live == 0 && !mapped && !pending); }
int main(void)
{
	unsigned total;
	reset(); ordinary(0); total = calls;
	for (unsigned i = 1; i <= total; i++) {
		reset(); fail_at = i;
		int result = run_compute(makedev(180, 128));
		CHECK(calls >= i && result != 0);
		if (pending) { CHECK(result == PENDING_EXIT && live != 0 && mapped); }
		else CHECK(result == 1 && live == 0 && !mapped);
	}
	for (unsigned i = 1; i <= 6; i++) { reset(); mismatch = i; ordinary(1); CHECK(!dispatched); }
	reset(); duplicate = 1; ordinary(1); CHECK(!dispatched);
	reset(); no_queue = 1; ordinary(1);
	reset(); no_memory = 1; ordinary(1);
	reset(); no_write = 1; ordinary(1); CHECK(completed);
	reset(); bad_word = 1; ordinary(1); CHECK(completed);
	reset(); partial_pipeline = 1; ordinary(1);
	reset(); timeout_wait = 1; CHECK(run_compute(makedev(180, 128)) == PENDING_EXIT); CHECK(pending && live != 0 && mapped);
	reset();
	printf("PASS: %u actual-consumer API/ownership checks; %u injected failures; no real GPU execution\n", checks, total);
	return 0;
}
