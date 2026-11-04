/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). D24 clear and depth-write
 * regression. */
#include <vulkan/vulkan.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "depth-shaders.h"

#define WIDTH 64U
#define HEIGHT 64U
#define ROW 68U
#define ROWS 66U
#define GUARD 64U
#define BYTES (2U * GUARD + ROW * ROWS * 4U)
#define POISON 0xa5U
#define CHECK(call)                                                            \
	do {                                                                   \
		VkResult result_ = (call);                                     \
		if (result_ != VK_SUCCESS) {                                   \
			fprintf(stderr, "%s: %d\n", #call, result_);           \
			return 2;                                              \
		}                                                              \
	} while (0)

static VkDeviceMemory
memory(VkDevice device, const VkPhysicalDeviceMemoryProperties *properties,
    const VkMemoryRequirements *requirements, VkMemoryPropertyFlags flags)
{
	VkDeviceMemory result = VK_NULL_HANDLE;
	VkMemoryAllocateInfo info = {
	    .sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
	    .allocationSize = requirements->size,
	};
	if (!requirements->size || requirements->size > 16U * 1024U * 1024U)
		return result;
	for (uint32_t i = 0; i < properties->memoryTypeCount; i++) {
		if ((requirements->memoryTypeBits & (1U << i)) &&
		    (properties->memoryTypes[i].propertyFlags & flags) ==
			flags) {
			info.memoryTypeIndex = i;
			if (vkAllocateMemory(device, &info, NULL, &result) !=
			    VK_SUCCESS)
				return VK_NULL_HANDLE;
			return result;
		}
	}
	return result;
}

int
main(int argc, char **argv)
{
	if (argc != 2 ||
	    (strcmp(argv[1], "0") && strcmp(argv[1], ".5") &&
		strcmp(argv[1], "1"))) {
		fprintf(stderr, "Usage: depth-check {0|.5|1}\n");
		return 2;
	}
	const float clear_depth = strtof(argv[1], NULL);
	const float depths[4] = {0, .25f, .75f, 1};
	const float colors[4][4] = {
	    {1, 0, 0, 1},
	    {0, 1, 0, 1},
	    {0, 0, 1, 1},
	    {1, 1, 1, 1},
	};
	VkApplicationInfo app = {
	    .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
	    .pApplicationName = "EmberBSD D24 clear check",
	    .apiVersion = VK_API_VERSION_1_2,
	};
	VkInstanceCreateInfo ici = {
	    .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
	    .pApplicationInfo = &app,
	};
	VkInstance instance;
	CHECK(vkCreateInstance(&ici, NULL, &instance));
	uint32_t count = 0;
	CHECK(vkEnumeratePhysicalDevices(instance, &count, NULL));
	if (count != 1)
		return 2;
	VkPhysicalDevice physical;
	CHECK(vkEnumeratePhysicalDevices(instance, &count, &physical));
	VkPhysicalDeviceProperties props;
	vkGetPhysicalDeviceProperties(physical, &props);
	if (props.vendorID != 0x1010 || !strstr(props.deviceName, "GE8300"))
		return 2;
	printf("GPU %s; clear=%g; D24S8 LESS/write\n", props.deviceName,
	    (double)clear_depth);
	vkGetPhysicalDeviceQueueFamilyProperties(physical, &count, NULL);
	if (!count || count > 32)
		return 2;
	VkQueueFamilyProperties families[32];
	vkGetPhysicalDeviceQueueFamilyProperties(physical, &count, families);
	uint32_t family;
	for (family = 0; family < count; family++)
		if (families[family].queueCount &&
		    (families[family].queueFlags & VK_QUEUE_GRAPHICS_BIT))
			break;
	if (family == count)
		return 2;
	const float priority = 1;
	VkDeviceQueueCreateInfo qci = {
	    .sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
	    .queueFamilyIndex = family,
	    .queueCount = 1,
	    .pQueuePriorities = &priority,
	};
	VkDeviceCreateInfo dci = {
	    .sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
	    .queueCreateInfoCount = 1,
	    .pQueueCreateInfos = &qci,
	};
	VkDevice device;
	CHECK(vkCreateDevice(physical, &dci, NULL, &device));
	VkQueue queue;
	vkGetDeviceQueue(device, family, 0, &queue);
	VkPhysicalDeviceMemoryProperties memory_properties;
	vkGetPhysicalDeviceMemoryProperties(physical, &memory_properties);
	VkImage images[2];
	VkImageView views[2];
	VkDeviceMemory image_memory[2];
	const VkFormat formats[2] = {
	    VK_FORMAT_R8G8B8A8_UNORM, VK_FORMAT_D24_UNORM_S8_UINT};
	for (unsigned i = 0; i < 2; i++) {
		VkImageCreateInfo ii = {
		    .sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
		    .imageType = VK_IMAGE_TYPE_2D,
		    .format = formats[i],
		    .extent = {WIDTH, HEIGHT, 1},
		    .mipLevels = 1,
		    .arrayLayers = 1,
		    .samples = VK_SAMPLE_COUNT_1_BIT,
		    .tiling = VK_IMAGE_TILING_OPTIMAL,
		    .usage = i ? VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT
			       : VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT |
			    VK_IMAGE_USAGE_TRANSFER_SRC_BIT,
		    .sharingMode = VK_SHARING_MODE_EXCLUSIVE,
		};
		CHECK(vkCreateImage(device, &ii, NULL, &images[i]));
		VkMemoryRequirements req;
		vkGetImageMemoryRequirements(device, images[i], &req);
		image_memory[i] = memory(device, &memory_properties, &req, 0);
		if (!image_memory[i])
			return 2;
		CHECK(vkBindImageMemory(device, images[i], image_memory[i], 0));
		VkImageViewCreateInfo vi = {
		    .sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
		    .image = images[i],
		    .viewType = VK_IMAGE_VIEW_TYPE_2D,
		    .format = formats[i],
		    .subresourceRange = {i ? VK_IMAGE_ASPECT_DEPTH_BIT |
				VK_IMAGE_ASPECT_STENCIL_BIT
					   : VK_IMAGE_ASPECT_COLOR_BIT,
			0, 1, 0, 1},
		};
		CHECK(vkCreateImageView(device, &vi, NULL, &views[i]));
	}
	VkBufferCreateInfo bci = {
	    .sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
	    .size = BYTES,
	    .usage = VK_BUFFER_USAGE_TRANSFER_DST_BIT,
	    .sharingMode = VK_SHARING_MODE_EXCLUSIVE,
	};
	VkBuffer buffer;
	VkDeviceMemory buffer_memory;
	VkMemoryRequirements req;
	CHECK(vkCreateBuffer(device, &bci, NULL, &buffer));
	vkGetBufferMemoryRequirements(device, buffer, &req);
	buffer_memory = memory(device, &memory_properties, &req,
	    VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
		VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
	if (!buffer_memory)
		return 2;
	CHECK(vkBindBufferMemory(device, buffer, buffer_memory, 0));
	void *mapped;
	CHECK(vkMapMemory(device, buffer_memory, 0, BYTES, 0, &mapped));
	memset(mapped, POISON, BYTES);
	VkAttachmentDescription attachments[2] = {
	    {.format = formats[0],
		.samples = VK_SAMPLE_COUNT_1_BIT,
		.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR,
		.storeOp = VK_ATTACHMENT_STORE_OP_STORE,
		.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE,
		.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE,
		.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
		.finalLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL},
	    {.format = formats[1],
		.samples = VK_SAMPLE_COUNT_1_BIT,
		.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR,
		.storeOp = VK_ATTACHMENT_STORE_OP_DONT_CARE,
		.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_CLEAR,
		.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE,
		.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
		.finalLayout =
		    VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL},
	};
	VkAttachmentReference color_ref = {
	    0, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL};
	VkAttachmentReference depth_ref = {
	    1, VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL};
	VkSubpassDescription subpass = {
	    .pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS,
	    .colorAttachmentCount = 1,
	    .pColorAttachments = &color_ref,
	    .pDepthStencilAttachment = &depth_ref};
	VkRenderPassCreateInfo rpci = {
	    .sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO,
	    .attachmentCount = 2,
	    .pAttachments = attachments,
	    .subpassCount = 1,
	    .pSubpasses = &subpass};
	VkRenderPass pass;
	CHECK(vkCreateRenderPass(device, &rpci, NULL, &pass));
	VkFramebufferCreateInfo fci = {
	    .sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO,
	    .renderPass = pass,
	    .attachmentCount = 2,
	    .pAttachments = views,
	    .width = WIDTH,
	    .height = HEIGHT,
	    .layers = 1};
	VkFramebuffer frame;
	CHECK(vkCreateFramebuffer(device, &fci, NULL, &frame));
	VkPushConstantRange range = {
	    VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0, 20};
	VkPipelineLayoutCreateInfo lci = {
	    .sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
	    .pushConstantRangeCount = 1,
	    .pPushConstantRanges = &range};
	VkPipelineLayout layout;
	CHECK(vkCreatePipelineLayout(device, &lci, NULL, &layout));
	VkShaderModule shaders[2];
	VkShaderModuleCreateInfo sci = {
	    .sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
	    .codeSize = sizeof(depth_vertex),
	    .pCode = depth_vertex};
	CHECK(vkCreateShaderModule(device, &sci, NULL, &shaders[0]));
	sci.codeSize = sizeof(depth_fragment);
	sci.pCode = depth_fragment;
	CHECK(vkCreateShaderModule(device, &sci, NULL, &shaders[1]));
	VkPipelineShaderStageCreateInfo stages[2] = {
	    {.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
		.stage = VK_SHADER_STAGE_VERTEX_BIT,
		.module = shaders[0],
		.pName = "main"},
	    {.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
		.stage = VK_SHADER_STAGE_FRAGMENT_BIT,
		.module = shaders[1],
		.pName = "main"},
	};
	VkPipelineVertexInputStateCreateInfo vertex = {
	    .sType = VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
	VkPipelineInputAssemblyStateCreateInfo assembly = {
	    .sType =
		VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO,
	    .topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST};
	VkViewport viewport = {0, 0, WIDTH, HEIGHT, 0, 1};
	VkPipelineViewportStateCreateInfo vp = {
	    .sType = VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO,
	    .viewportCount = 1,
	    .pViewports = &viewport,
	    .scissorCount = 1};
	VkDynamicState scissor_dynamic = VK_DYNAMIC_STATE_SCISSOR;
	VkPipelineDynamicStateCreateInfo dynamic = {
	    .sType = VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO,
	    .dynamicStateCount = 1,
	    .pDynamicStates = &scissor_dynamic};
	VkPipelineRasterizationStateCreateInfo raster = {
	    .sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO,
	    .polygonMode = VK_POLYGON_MODE_FILL,
	    .cullMode = VK_CULL_MODE_NONE,
	    .frontFace = VK_FRONT_FACE_COUNTER_CLOCKWISE,
	    .lineWidth = 1};
	VkPipelineMultisampleStateCreateInfo ms = {
	    .sType = VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO,
	    .rasterizationSamples = VK_SAMPLE_COUNT_1_BIT};
	VkPipelineDepthStencilStateCreateInfo ds = {
	    .sType = VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO,
	    .depthTestEnable = VK_TRUE,
	    .depthWriteEnable = VK_TRUE,
	    .depthCompareOp = VK_COMPARE_OP_LESS};
	VkPipelineColorBlendAttachmentState ca = {.colorWriteMask = 15};
	VkPipelineColorBlendStateCreateInfo blend = {
	    .sType = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO,
	    .attachmentCount = 1,
	    .pAttachments = &ca};
	VkGraphicsPipelineCreateInfo pci = {
	    .sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO,
	    .stageCount = 2,
	    .pStages = stages,
	    .pVertexInputState = &vertex,
	    .pInputAssemblyState = &assembly,
	    .pViewportState = &vp,
	    .pRasterizationState = &raster,
	    .pMultisampleState = &ms,
	    .pDepthStencilState = &ds,
	    .pColorBlendState = &blend,
	    .pDynamicState = &dynamic,
	    .layout = layout,
	    .renderPass = pass};
	VkPipeline pipeline;
	CHECK(vkCreateGraphicsPipelines(
	    device, VK_NULL_HANDLE, 1, &pci, NULL, &pipeline));
	VkCommandPoolCreateInfo cpci = {
	    .sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
	    .queueFamilyIndex = family};
	VkCommandPool pool;
	CHECK(vkCreateCommandPool(device, &cpci, NULL, &pool));
	VkCommandBufferAllocateInfo cbai = {
	    .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
	    .commandPool = pool,
	    .level = VK_COMMAND_BUFFER_LEVEL_PRIMARY,
	    .commandBufferCount = 1};
	VkCommandBuffer command;
	CHECK(vkAllocateCommandBuffers(device, &cbai, &command));
	VkCommandBufferBeginInfo cbi = {
	    .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
	    .flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT};
	CHECK(vkBeginCommandBuffer(command, &cbi));
	VkBufferMemoryBarrier barrier = {
	    .sType = VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER,
	    .srcAccessMask = VK_ACCESS_HOST_WRITE_BIT,
	    .dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT,
	    .srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
	    .dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
	    .buffer = buffer,
	    .size = VK_WHOLE_SIZE};
	vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_HOST_BIT,
	    VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 0, NULL, 1, &barrier, 0, NULL);
	VkClearValue clear[2] = {{.color.float32 = {1, 0, 1, 1}},
	    {.depthStencil = {clear_depth, 0}}};
	VkRenderPassBeginInfo rbi = {
	    .sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO,
	    .renderPass = pass,
	    .framebuffer = frame,
	    .renderArea = {{0, 0}, {WIDTH, HEIGHT}},
	    .clearValueCount = 2,
	    .pClearValues = clear};
	vkCmdBeginRenderPass(command, &rbi, VK_SUBPASS_CONTENTS_INLINE);
	vkCmdBindPipeline(command, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline);
	for (unsigned i = 0; i < 4; i++) {
		VkRect2D scissor = {{(int32_t)(i % 2 * WIDTH / 2),
					(int32_t)(i / 2 * HEIGHT / 2)},
		    {WIDTH / 2, HEIGHT / 2}};
		float values[5];
		memcpy(values, colors[i], sizeof(colors[i]));
		values[4] = depths[i];
		vkCmdSetScissor(command, 0, 1, &scissor);
		vkCmdPushConstants(command, layout, range.stageFlags, 0,
		    sizeof(values), values);
		vkCmdDraw(command, 3, 1, 0, 0);
		/* A later, farther cyan triangle must fail after the first
		 * depth write. */
		values[0] = 0;
		values[1] = 1;
		values[2] = 1;
		values[4] = depths[i] + .125f;
		vkCmdPushConstants(command, layout, range.stageFlags, 0,
		    sizeof(values), values);
		vkCmdDraw(command, 3, 1, 0, 0);
	}
	vkCmdEndRenderPass(command);
	VkImageMemoryBarrier ib = {
	    .sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER,
	    .srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
	    .dstAccessMask = VK_ACCESS_TRANSFER_READ_BIT,
	    .oldLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
	    .newLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
	    .srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
	    .dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
	    .image = images[0],
	    .subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1}};
	vkCmdPipelineBarrier(command,
	    VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
	    VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 0, NULL, 0, NULL, 1, &ib);
	VkBufferImageCopy region = {.bufferOffset = GUARD,
	    .bufferRowLength = ROW,
	    .bufferImageHeight = ROWS,
	    .imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1},
	    .imageExtent = {WIDTH, HEIGHT, 1}};
	vkCmdCopyImageToBuffer(command, images[0],
	    VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, buffer, 1, &region);
	barrier.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
	barrier.dstAccessMask = VK_ACCESS_HOST_READ_BIT;
	vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_TRANSFER_BIT,
	    VK_PIPELINE_STAGE_HOST_BIT, 0, 0, NULL, 1, &barrier, 0, NULL);
	CHECK(vkEndCommandBuffer(command));
	VkFenceCreateInfo fi = {.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
	VkFence fence;
	CHECK(vkCreateFence(device, &fi, NULL, &fence));
	VkSubmitInfo submit = {.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO,
	    .commandBufferCount = 1,
	    .pCommandBuffers = &command};
	CHECK(vkQueueSubmit(queue, 1, &submit, fence));
	CHECK(
	    vkWaitForFences(device, 1, &fence, VK_TRUE, UINT64_C(5000000000)));
	int status = 0;
	for (unsigned i = 0; i < BYTES; i++) {
		uint8_t expected = POISON;
		if (i >= GUARD) {
			unsigned offset = i - GUARD, y = offset / (ROW * 4),
				 x = offset / 4 % ROW, channel = offset % 4;
			if (x < WIDTH && y < HEIGHT) {
				unsigned quadrant =
				    (y >= HEIGHT / 2) * 2 + (x >= WIDTH / 2);
				expected =
				    (uint8_t)((depths[quadrant] < clear_depth
						      ? colors[quadrant]
							      [channel]
						      : (channel == 0 ||
								    channel ==
									2 ||
								    channel == 3
								? 1
								: 0)) *
					255);
			}
		}
		if (((uint8_t *)mapped)[i] != expected) {
			fprintf(stderr,
			    "Mismatch byte %u actual=%u expected=%u\n", i,
			    ((uint8_t *)mapped)[i], expected);
			status = 1;
			break;
		}
	}
	if (!status)
		printf(
		    "PASS: all pixels, row/tail padding and guards; clear=%g\n",
		    (double)clear_depth);
	vkDestroyFence(device, fence, NULL);
	vkDestroyCommandPool(device, pool, NULL);
	vkDestroyPipeline(device, pipeline, NULL);
	for (unsigned i = 0; i < 2; i++)
		vkDestroyShaderModule(device, shaders[i], NULL);
	vkDestroyPipelineLayout(device, layout, NULL);
	vkDestroyFramebuffer(device, frame, NULL);
	vkDestroyRenderPass(device, pass, NULL);
	vkUnmapMemory(device, buffer_memory);
	vkDestroyBuffer(device, buffer, NULL);
	vkFreeMemory(device, buffer_memory, NULL);
	for (unsigned i = 0; i < 2; i++) {
		vkDestroyImageView(device, views[i], NULL);
		vkDestroyImage(device, images[i], NULL);
		vkFreeMemory(device, image_memory[i], NULL);
	}
	vkDestroyDevice(device, NULL);
	vkDestroyInstance(instance, NULL);
	return status;
}
