/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). Offscreen Vulkan graphics acceptance. No software fallback. */
#include <sys/types.h>
#include <sys/stat.h>
#if defined(__linux__)
#include <sys/sysmacros.h>
#endif

#include <vulkan/vulkan.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static bool
has_drm_properties(VkPhysicalDevice device)
{
	VkExtensionProperties *extensions = NULL;
	uint32_t count = 0, i;
	VkResult result;
	bool found = false;

	result = vkEnumerateDeviceExtensionProperties(device, NULL, &count, NULL);
	if (result != VK_SUCCESS || count == 0 ||
	    (uint64_t)count * sizeof(*extensions) > SIZE_MAX)
		return false;
	extensions = calloc(count, sizeof(*extensions));
	if (extensions == NULL)
		return false;
	result = vkEnumerateDeviceExtensionProperties(device, NULL, &count,
	    extensions);
	if (result == VK_SUCCESS) {
		for (i = 0; i < count; i++) {
			if (strcmp(extensions[i].extensionName,
			    VK_EXT_PHYSICAL_DEVICE_DRM_EXTENSION_NAME) == 0)
				found = true;
		}
	}
	free(extensions);
	return found;
}

#include "powervr-offscreen-shaders.h"

#define WIDTH 16U
#define HEIGHT 16U
#define ROW_PIXELS 20U
#define BUFFER_ROWS 18U
#define GUARD_BYTES 64U
#define BUFFER_BYTES (2U * GUARD_BYTES + ROW_PIXELS * BUFFER_ROWS * 4U)
#define POISON 0xa5U
#define WAIT_NS UINT64_C(10000000000)
#define PENDING_EXIT 3
#define ALLOCATION_LIMIT (16U * 1024U * 1024U)

static VkPhysicalDevice
select_device(VkInstance instance, dev_t expected)
{
	VkPhysicalDevice *devices = NULL, selected = VK_NULL_HANDLE;
	uint32_t count = 0, i, matches = 0;
	VkResult result;

	result = vkEnumeratePhysicalDevices(instance, &count, NULL);
	if (result != VK_SUCCESS || count == 0 ||
	    (uint64_t)count * sizeof(*devices) > SIZE_MAX)
		return VK_NULL_HANDLE;
	devices = calloc(count, sizeof(*devices));
	if (devices == NULL)
		return VK_NULL_HANDLE;
	result = vkEnumeratePhysicalDevices(instance, &count, devices);
	if (result != VK_SUCCESS)
		goto out;
	for (i = 0; i < count; i++) {
		VkPhysicalDeviceDrmPropertiesEXT drm = {
			.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DRM_PROPERTIES_EXT,
		};
		VkPhysicalDeviceDriverProperties driver = {
			.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DRIVER_PROPERTIES,
			.pNext = &drm,
		};
		VkPhysicalDeviceProperties2 properties = {
			.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2,
			.pNext = &driver,
		};

		if (!has_drm_properties(devices[i]))
			continue;
		vkGetPhysicalDeviceProperties2(devices[i], &properties);
		if (properties.properties.vendorID != 0x1010 ||
		    driver.driverID != VK_DRIVER_ID_IMAGINATION_OPEN_SOURCE_MESA ||
		    !drm.hasRender || drm.renderMajor != (int64_t)major(expected) ||
		    drm.renderMinor != (int64_t)minor(expected) ||
		    properties.properties.apiVersion < VK_API_VERSION_1_2)
			continue;
		selected = devices[i];
		matches++;
		printf("PowerVR: %s; driver=%s; render=%" PRId64 ":%" PRId64 "\n",
		    properties.properties.deviceName, driver.driverName,
		    drm.renderMajor, drm.renderMinor);
	}
out:
	free(devices);
	return matches == 1 ? selected : VK_NULL_HANDLE;
}

static bool
select_queue(VkPhysicalDevice physical, uint32_t *family)
{
	VkQueueFamilyProperties *properties;
	uint32_t count = 0, i;
	bool found = false;

	vkGetPhysicalDeviceQueueFamilyProperties(physical, &count, NULL);
	if (count == 0 || (uint64_t)count * sizeof(*properties) > SIZE_MAX)
		return false;
	properties = calloc(count, sizeof(*properties));
	if (properties == NULL)
		return false;
	vkGetPhysicalDeviceQueueFamilyProperties(physical, &count, properties);
	for (i = 0; i < count; i++) {
		if (properties[i].queueCount != 0 &&
		    (properties[i].queueFlags & VK_QUEUE_GRAPHICS_BIT) != 0) {
			*family = i;
			found = true;
			break;
		}
	}
	free(properties);
	return found;
}

#define TRY(call) do { \
	result = (call); \
	if (result != VK_SUCCESS) { \
		fprintf(stderr, "%s: %d\n", #call, result); \
		goto out; \
	} \
} while (0)

/* Buffer copy uses explicit row length. Optimal images have no host row pitch. */
static bool
check_pixels(const uint8_t *bytes)
{
	unsigned i, row, col, channel, x, y;
	uint8_t expected;
	bool inside;

	for (i = 0; i < BUFFER_BYTES; i++) {
		expected = POISON;
		if (i >= GUARD_BYTES) {
			row = (i - GUARD_BYTES) / (ROW_PIXELS * 4U);
			col = ((i - GUARD_BYTES) / 4U) % ROW_PIXELS;
			channel = (i - GUARD_BYTES) % 4U;
			if (row < HEIGHT && col < WIDTH) {
				/* Pixel centers are never on either triangle edge. */
				x = 2U * col + 1U;
				y = 2U * row + 1U;
				inside = 2U * x > y && 2U * x + y < 4U * WIDTH;
				expected = channel == 3 ||
				    (channel == 0 && !inside) ||
				    (channel == 1 && inside) ? 255 : 0;
			}
		}
		if (bytes[i] != expected) {
			fprintf(stderr, "Readback byte %u: %u expected %u\n",
			    i, bytes[i], expected);
			return false;
		}
	}
	return true;
}

static VkResult
allocate_memory(VkDevice device, const VkPhysicalDeviceMemoryProperties *props,
    const VkMemoryRequirements *req, VkMemoryPropertyFlags flags,
    VkDeviceMemory *memory)
{
	uint32_t i;
	VkMemoryAllocateInfo info = {
		.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
		.allocationSize = req->size,
	};

	if (req->size == 0 || req->size > ALLOCATION_LIMIT ||
	    props->memoryTypeCount > VK_MAX_MEMORY_TYPES)
		return VK_ERROR_OUT_OF_DEVICE_MEMORY;
	for (i = 0; i < props->memoryTypeCount; i++) {
		if ((req->memoryTypeBits & (UINT32_C(1) << i)) != 0 &&
		    (props->memoryTypes[i].propertyFlags & flags) == flags) {
			info.memoryTypeIndex = i;
			return vkAllocateMemory(device, &info, NULL, memory);
		}
	}
	return VK_ERROR_FEATURE_NOT_PRESENT;
}

/* Failed or uncertain submitted work must not trigger unsafe user cleanup. */
static int
run_offscreen(dev_t expected)
{
	VkInstance instance = VK_NULL_HANDLE;
	VkPhysicalDevice physical;
	VkDevice device = VK_NULL_HANDLE;
	VkImage image = VK_NULL_HANDLE;
	VkImageView view = VK_NULL_HANDLE;
	VkDeviceMemory image_memory = VK_NULL_HANDLE, buffer_memory = VK_NULL_HANDLE;
	VkBuffer buffer = VK_NULL_HANDLE;
	VkRenderPass render_pass = VK_NULL_HANDLE;
	VkFramebuffer framebuffer = VK_NULL_HANDLE;
	VkPipelineLayout layout = VK_NULL_HANDLE;
	VkPipeline pipeline = VK_NULL_HANDLE;
	VkShaderModule vertex = VK_NULL_HANDLE, fragment = VK_NULL_HANDLE;
	VkCommandPool pool = VK_NULL_HANDLE;
	VkFence fence = VK_NULL_HANDLE;
	VkCommandBuffer command;
	VkQueue queue;
	VkPhysicalDeviceMemoryProperties properties;
	VkMemoryRequirements requirements;
	VkFormatProperties format_properties;
	VkImageFormatProperties image_properties;
	VkResult result;
	uint32_t family;
	void *address = NULL;
	bool mapped = false;
	int status = 1;
	const float priority = 1.0f;
	const VkFormat format = VK_FORMAT_R8G8B8A8_UNORM;
	const VkImageUsageFlags usage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT |
	    VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
	const VkFormatFeatureFlags needed = VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BIT |
	    VK_FORMAT_FEATURE_TRANSFER_SRC_BIT;
	const VkApplicationInfo app = {
		.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
		.pApplicationName = "EmberBSD PowerVR offscreen check",
		.apiVersion = VK_API_VERSION_1_2,
	};
	const VkInstanceCreateInfo instance_info = {
		.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
		.pApplicationInfo = &app,
	};

	TRY(vkCreateInstance(&instance_info, NULL, &instance));
	physical = select_device(instance, expected);
	if (physical == VK_NULL_HANDLE || !select_queue(physical, &family)) {
		fprintf(stderr, "Require one matching PowerVR device and graphics queue\n");
		goto out;
	}
	vkGetPhysicalDeviceFormatProperties(physical, format, &format_properties);
	if ((format_properties.optimalTilingFeatures & needed) != needed) {
		fprintf(stderr, "RGBA8 optimal color/transfer support is required\n");
		goto out;
	}
	TRY(vkGetPhysicalDeviceImageFormatProperties(physical, format,
	    VK_IMAGE_TYPE_2D, VK_IMAGE_TILING_OPTIMAL, usage, 0, &image_properties));
	if (image_properties.maxExtent.width < WIDTH ||
	    image_properties.maxExtent.height < HEIGHT ||
	    image_properties.maxExtent.depth < 1 || image_properties.maxMipLevels < 1 ||
	    image_properties.maxArrayLayers < 1 ||
	    (image_properties.sampleCounts & VK_SAMPLE_COUNT_1_BIT) == 0) {
		fprintf(stderr, "RGBA8 image properties do not cover the requested image\n");
		goto out;
	}
	VkDeviceQueueCreateInfo queue_info = {
		.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
		.queueFamilyIndex = family, .queueCount = 1,
		.pQueuePriorities = &priority,
	};
	VkDeviceCreateInfo device_info = {
		.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
		.queueCreateInfoCount = 1, .pQueueCreateInfos = &queue_info,
	};
	TRY(vkCreateDevice(physical, &device_info, NULL, &device));
	vkGetDeviceQueue(device, family, 0, &queue);
	vkGetPhysicalDeviceMemoryProperties(physical, &properties);
	VkImageCreateInfo image_info = {
		.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
		.imageType = VK_IMAGE_TYPE_2D, .format = format,
		.extent = { WIDTH, HEIGHT, 1 }, .mipLevels = 1, .arrayLayers = 1,
		.samples = VK_SAMPLE_COUNT_1_BIT, .tiling = VK_IMAGE_TILING_OPTIMAL,
		.usage = usage, .sharingMode = VK_SHARING_MODE_EXCLUSIVE,
		.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
	};
	TRY(vkCreateImage(device, &image_info, NULL, &image));
	vkGetImageMemoryRequirements(device, image, &requirements);
	TRY(allocate_memory(device, &properties, &requirements, 0, &image_memory));
	TRY(vkBindImageMemory(device, image, image_memory, 0));
	VkImageViewCreateInfo view_info = {
		.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
		.image = image, .viewType = VK_IMAGE_VIEW_TYPE_2D, .format = format,
		.subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1 },
	};
	TRY(vkCreateImageView(device, &view_info, NULL, &view));
	VkBufferCreateInfo buffer_info = {
		.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
		.size = BUFFER_BYTES, .usage = VK_BUFFER_USAGE_TRANSFER_DST_BIT,
		.sharingMode = VK_SHARING_MODE_EXCLUSIVE,
	};
	TRY(vkCreateBuffer(device, &buffer_info, NULL, &buffer));
	vkGetBufferMemoryRequirements(device, buffer, &requirements);
	if (requirements.size < BUFFER_BYTES)
		goto out;
	TRY(allocate_memory(device, &properties, &requirements,
	    VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT, &buffer_memory));
	TRY(vkBindBufferMemory(device, buffer, buffer_memory, 0));
	TRY(vkMapMemory(device, buffer_memory, 0, VK_WHOLE_SIZE, 0, &address));
	mapped = true;
	memset(address, POISON, (size_t)requirements.size);
	VkMappedMemoryRange range = {
		.sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE,
		.memory = buffer_memory, .offset = 0, .size = VK_WHOLE_SIZE,
	};
	TRY(vkFlushMappedMemoryRanges(device, 1, &range));
	VkAttachmentDescription attachment = {
		.format = format, .samples = VK_SAMPLE_COUNT_1_BIT,
		.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR, .storeOp = VK_ATTACHMENT_STORE_OP_STORE,
		.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE,
		.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE,
		.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
		.finalLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
	};
	VkAttachmentReference color = { 0, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL };
	VkSubpassDescription subpass = {
		.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS,
		.colorAttachmentCount = 1, .pColorAttachments = &color,
	};
	VkSubpassDependency dependency = {
		.srcSubpass = VK_SUBPASS_EXTERNAL, .dstSubpass = 0,
		.srcStageMask = VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
		.dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
		.dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
	};
	VkRenderPassCreateInfo pass_info = {
		.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO,
		.attachmentCount = 1, .pAttachments = &attachment,
		.subpassCount = 1, .pSubpasses = &subpass,
		.dependencyCount = 1, .pDependencies = &dependency,
	};
	TRY(vkCreateRenderPass(device, &pass_info, NULL, &render_pass));
	VkFramebufferCreateInfo framebuffer_info = {
		.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO,
		.renderPass = render_pass, .attachmentCount = 1, .pAttachments = &view,
		.width = WIDTH, .height = HEIGHT, .layers = 1,
	};
	TRY(vkCreateFramebuffer(device, &framebuffer_info, NULL, &framebuffer));
	VkPipelineLayoutCreateInfo layout_info = {
		.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
	};
	TRY(vkCreatePipelineLayout(device, &layout_info, NULL, &layout));
	VkShaderModuleCreateInfo shader_info = {
		.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
		.codeSize = sizeof(vertex_shader), .pCode = vertex_shader,
	};
	TRY(vkCreateShaderModule(device, &shader_info, NULL, &vertex));
	shader_info.codeSize = sizeof(fragment_shader);
	shader_info.pCode = fragment_shader;
	TRY(vkCreateShaderModule(device, &shader_info, NULL, &fragment));
	VkPipelineShaderStageCreateInfo stages[2] = {
		{ .sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
		  .stage = VK_SHADER_STAGE_VERTEX_BIT, .module = vertex, .pName = "main" },
		{ .sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
		  .stage = VK_SHADER_STAGE_FRAGMENT_BIT, .module = fragment, .pName = "main" },
	};
	VkPipelineVertexInputStateCreateInfo vertex_input = {
		.sType = VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO,
	};
	VkPipelineInputAssemblyStateCreateInfo assembly = {
		.sType = VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO,
		.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST,
	};
	VkViewport viewport = { 0, 0, WIDTH, HEIGHT, 0, 1 };
	VkRect2D scissor = { { 0, 0 }, { WIDTH, HEIGHT } };
	VkPipelineViewportStateCreateInfo viewport_info = {
		.sType = VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO,
		.viewportCount = 1, .pViewports = &viewport,
		.scissorCount = 1, .pScissors = &scissor,
	};
	VkPipelineRasterizationStateCreateInfo raster = {
		.sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO,
		.polygonMode = VK_POLYGON_MODE_FILL, .cullMode = VK_CULL_MODE_NONE,
		.frontFace = VK_FRONT_FACE_COUNTER_CLOCKWISE, .lineWidth = 1.0f,
	};
	VkPipelineMultisampleStateCreateInfo multisample = {
		.sType = VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO,
		.rasterizationSamples = VK_SAMPLE_COUNT_1_BIT,
	};
	VkPipelineColorBlendAttachmentState blend_attachment = {
		.colorWriteMask = VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
		    VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT,
	};
	VkPipelineColorBlendStateCreateInfo blend = {
		.sType = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO,
		.attachmentCount = 1, .pAttachments = &blend_attachment,
	};
	VkGraphicsPipelineCreateInfo pipeline_info = {
		.sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO,
		.stageCount = 2, .pStages = stages, .pVertexInputState = &vertex_input,
		.pInputAssemblyState = &assembly, .pViewportState = &viewport_info,
		.pRasterizationState = &raster, .pMultisampleState = &multisample,
		.pColorBlendState = &blend, .layout = layout, .renderPass = render_pass,
	};
	TRY(vkCreateGraphicsPipelines(device, VK_NULL_HANDLE, 1, &pipeline_info,
	    NULL, &pipeline));
	VkCommandPoolCreateInfo pool_info = {
		.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
		.queueFamilyIndex = family,
	};
	TRY(vkCreateCommandPool(device, &pool_info, NULL, &pool));
	VkCommandBufferAllocateInfo command_info = {
		.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
		.commandPool = pool, .level = VK_COMMAND_BUFFER_LEVEL_PRIMARY,
		.commandBufferCount = 1,
	};
	TRY(vkAllocateCommandBuffers(device, &command_info, &command));
	VkCommandBufferBeginInfo begin = {
		.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
		.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT,
	};
	TRY(vkBeginCommandBuffer(command, &begin));
	VkBufferMemoryBarrier buffer_barrier = {
		.sType = VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER,
		.srcAccessMask = VK_ACCESS_HOST_WRITE_BIT,
		.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT,
		.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
		.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
		.buffer = buffer, .offset = 0, .size = VK_WHOLE_SIZE,
	};
	vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_HOST_BIT,
	    VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 0, NULL, 1, &buffer_barrier, 0, NULL);
	VkClearValue clear = { .color.float32 = { 1, 0, 0, 1 } };
	VkRenderPassBeginInfo pass_begin = {
		.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO,
		.renderPass = render_pass, .framebuffer = framebuffer,
		.renderArea = { { 0, 0 }, { WIDTH, HEIGHT } },
		.clearValueCount = 1, .pClearValues = &clear,
	};
	vkCmdBeginRenderPass(command, &pass_begin, VK_SUBPASS_CONTENTS_INLINE);
	vkCmdBindPipeline(command, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline);
	vkCmdDraw(command, 3, 1, 0, 0);
	vkCmdEndRenderPass(command);
	VkImageMemoryBarrier image_barrier = {
		.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER,
		.srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
		.dstAccessMask = VK_ACCESS_TRANSFER_READ_BIT,
		.oldLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
		.newLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
		.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
		.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
		.image = image,
		.subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1 },
	};
	vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
	    VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 0, NULL, 0, NULL, 1, &image_barrier);
	VkBufferImageCopy copy = {
		.bufferOffset = GUARD_BYTES, .bufferRowLength = ROW_PIXELS,
		.bufferImageHeight = BUFFER_ROWS,
		.imageSubresource = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1 },
		.imageExtent = { WIDTH, HEIGHT, 1 },
	};
	vkCmdCopyImageToBuffer(command, image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
	    buffer, 1, &copy);
	buffer_barrier.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
	buffer_barrier.dstAccessMask = VK_ACCESS_HOST_READ_BIT;
	vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_TRANSFER_BIT,
	    VK_PIPELINE_STAGE_HOST_BIT, 0, 0, NULL, 1, &buffer_barrier, 0, NULL);
	TRY(vkEndCommandBuffer(command));
	VkFenceCreateInfo fence_info = { .sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO };
	TRY(vkCreateFence(device, &fence_info, NULL, &fence));
	VkSubmitInfo submit = {
		.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO,
		.commandBufferCount = 1, .pCommandBuffers = &command,
	};
	result = vkQueueSubmit(queue, 1, &submit, fence);
	if (result != VK_SUCCESS) {
		fprintf(stderr, "Submission not accepted: %d; retain possibly active resources\n", result);
		return PENDING_EXIT;
	}
	result = vkWaitForFences(device, 1, &fence, VK_TRUE, WAIT_NS);
	if (result != VK_SUCCESS) {
		fprintf(stderr, "Fence not accepted: %d; retain possibly active resources\n", result);
		return PENDING_EXIT;
	}
	TRY(vkInvalidateMappedMemoryRanges(device, 1, &range));
	if (!check_pixels(address))
		goto out;
	puts("PASS: optimal-image triangle, all 256 RGBA pixels, row padding and guards");
	status = 0;
out:
	if (fence != VK_NULL_HANDLE) vkDestroyFence(device, fence, NULL);
	if (pool != VK_NULL_HANDLE) vkDestroyCommandPool(device, pool, NULL);
	if (pipeline != VK_NULL_HANDLE) vkDestroyPipeline(device, pipeline, NULL);
	if (vertex != VK_NULL_HANDLE) vkDestroyShaderModule(device, vertex, NULL);
	if (fragment != VK_NULL_HANDLE) vkDestroyShaderModule(device, fragment, NULL);
	if (layout != VK_NULL_HANDLE) vkDestroyPipelineLayout(device, layout, NULL);
	if (framebuffer != VK_NULL_HANDLE) vkDestroyFramebuffer(device, framebuffer, NULL);
	if (render_pass != VK_NULL_HANDLE) vkDestroyRenderPass(device, render_pass, NULL);
	if (view != VK_NULL_HANDLE) vkDestroyImageView(device, view, NULL);
	if (image != VK_NULL_HANDLE) vkDestroyImage(device, image, NULL);
	if (image_memory != VK_NULL_HANDLE) vkFreeMemory(device, image_memory, NULL);
	if (mapped) vkUnmapMemory(device, buffer_memory);
	if (buffer != VK_NULL_HANDLE) vkDestroyBuffer(device, buffer, NULL);
	if (buffer_memory != VK_NULL_HANDLE) vkFreeMemory(device, buffer_memory, NULL);
	if (device != VK_NULL_HANDLE) vkDestroyDevice(device, NULL);
	if (instance != VK_NULL_HANDLE) vkDestroyInstance(instance, NULL);
	return status;
}

int
main(int argc, char **argv)
{
	struct stat st;
	int result;

	if (argc != 2) {
		fprintf(stderr, "Usage: %s RENDER_NODE\n", argv[0]);
		return 2;
	}
	if (stat(argv[1], &st) != 0 || !S_ISCHR(st.st_mode)) {
		fprintf(stderr, "Not a character device: %s\n", argv[1]);
		return 1;
	}
	result = run_offscreen(st.st_rdev);
	if (result == PENDING_EXIT) {
		fflush(NULL);
		_Exit(result);
	}
	return result;
}
