/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). Standard Vulkan compute acceptance. No software fallback. */
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

#include "powervr-compute-shader.h"

#define WORDS 16U
#define VALUE UINT32_C(0x13579bdf)
#define POISON UINT32_C(0xdeadbeef)
#define WAIT_NS UINT64_C(10000000000)
#define PENDING_EXIT 3

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
		    (properties[i].queueFlags & VK_QUEUE_COMPUTE_BIT) != 0) {
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

/* Return PENDING_EXIT without destroying resources which may still be in use. */
static int
run_compute(dev_t expected)
{
	VkInstance instance = VK_NULL_HANDLE;
	VkPhysicalDevice physical;
	VkDevice device = VK_NULL_HANDLE;
	VkBuffer buffer = VK_NULL_HANDLE;
	VkDeviceMemory memory = VK_NULL_HANDLE;
	VkDescriptorSetLayout set_layout = VK_NULL_HANDLE;
	VkPipelineLayout pipeline_layout = VK_NULL_HANDLE;
	VkShaderModule shader = VK_NULL_HANDLE;
	VkPipeline pipeline = VK_NULL_HANDLE;
	VkDescriptorPool descriptor_pool = VK_NULL_HANDLE;
	VkCommandPool command_pool = VK_NULL_HANDLE;
	VkFence fence = VK_NULL_HANDLE;
	VkDescriptorSet set;
	VkCommandBuffer command;
	VkQueue queue;
	VkPhysicalDeviceMemoryProperties properties;
	VkMemoryRequirements requirements;
	uint32_t family, type, i;
	void *address = NULL;
	bool mapped = false;
	VkResult result;
	int status = 1;
	const float priority = 1.0f;
	const VkApplicationInfo app = {
		.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
		.pApplicationName = "EmberBSD PowerVR compute check",
		.apiVersion = VK_API_VERSION_1_2,
	};
	const VkInstanceCreateInfo instance_info = {
		.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
		.pApplicationInfo = &app,
	};

	TRY(vkCreateInstance(&instance_info, NULL, &instance));
	physical = select_device(instance, expected);
	if (physical == VK_NULL_HANDLE || !select_queue(physical, &family)) {
		fprintf(stderr, "Require one matching PowerVR device and compute queue\n");
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
	puts("PASS: vkCreateDevice");
	vkGetDeviceQueue(device, family, 0, &queue);
	VkBufferCreateInfo buffer_info = {
		.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
		.size = WORDS * sizeof(uint32_t),
		.usage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT,
		.sharingMode = VK_SHARING_MODE_EXCLUSIVE,
	};
	TRY(vkCreateBuffer(device, &buffer_info, NULL, &buffer));
	vkGetBufferMemoryRequirements(device, buffer, &requirements);
	vkGetPhysicalDeviceMemoryProperties(physical, &properties);
	for (type = 0; type < properties.memoryTypeCount; type++) {
		if ((requirements.memoryTypeBits & (UINT32_C(1) << type)) != 0 &&
		    (properties.memoryTypes[type].propertyFlags &
		    VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT) != 0)
			break;
	}
	if (type == properties.memoryTypeCount) {
		fprintf(stderr, "No compatible host-visible storage memory\n");
		goto out;
	}
	VkMemoryAllocateInfo memory_info = {
		.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
		.allocationSize = requirements.size, .memoryTypeIndex = type,
	};
	TRY(vkAllocateMemory(device, &memory_info, NULL, &memory));
	TRY(vkBindBufferMemory(device, buffer, memory, 0));
	TRY(vkMapMemory(device, memory, 0, VK_WHOLE_SIZE, 0, &address));
	mapped = true;
	for (i = 0; i < WORDS; i++)
		((uint32_t *)address)[i] = POISON;
	VkMappedMemoryRange range = {
		.sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE,
		.memory = memory, .offset = 0, .size = VK_WHOLE_SIZE,
	};
	TRY(vkFlushMappedMemoryRanges(device, 1, &range));
	VkDescriptorSetLayoutBinding binding = {
		.binding = 0, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
		.descriptorCount = 1, .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT,
	};
	VkDescriptorSetLayoutCreateInfo set_info = {
		.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
		.bindingCount = 1, .pBindings = &binding,
	};
	TRY(vkCreateDescriptorSetLayout(device, &set_info, NULL, &set_layout));
	VkPipelineLayoutCreateInfo layout_info = {
		.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
		.setLayoutCount = 1, .pSetLayouts = &set_layout,
	};
	TRY(vkCreatePipelineLayout(device, &layout_info, NULL, &pipeline_layout));
	VkShaderModuleCreateInfo shader_info = {
		.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
		.codeSize = sizeof(compute_shader), .pCode = compute_shader,
	};
	TRY(vkCreateShaderModule(device, &shader_info, NULL, &shader));
	VkComputePipelineCreateInfo pipeline_info = {
		.sType = VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO,
		.stage = {
			.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
			.stage = VK_SHADER_STAGE_COMPUTE_BIT,
			.module = shader, .pName = "main",
		},
		.layout = pipeline_layout,
	};
	TRY(vkCreateComputePipelines(device, VK_NULL_HANDLE, 1, &pipeline_info,
	    NULL, &pipeline));
	VkDescriptorPoolSize pool_size = {
		.type = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, .descriptorCount = 1,
	};
	VkDescriptorPoolCreateInfo pool_info = {
		.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
		.maxSets = 1, .poolSizeCount = 1, .pPoolSizes = &pool_size,
	};
	TRY(vkCreateDescriptorPool(device, &pool_info, NULL, &descriptor_pool));
	VkDescriptorSetAllocateInfo set_allocate = {
		.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
		.descriptorPool = descriptor_pool, .descriptorSetCount = 1,
		.pSetLayouts = &set_layout,
	};
	TRY(vkAllocateDescriptorSets(device, &set_allocate, &set));
	VkDescriptorBufferInfo descriptor = {
		.buffer = buffer, .offset = 0, .range = buffer_info.size,
	};
	VkWriteDescriptorSet write = {
		.sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
		.dstSet = set, .dstBinding = 0, .descriptorCount = 1,
		.descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
		.pBufferInfo = &descriptor,
	};
	vkUpdateDescriptorSets(device, 1, &write, 0, NULL);
	VkCommandPoolCreateInfo command_info = {
		.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
		.queueFamilyIndex = family,
	};
	TRY(vkCreateCommandPool(device, &command_info, NULL, &command_pool));
	VkCommandBufferAllocateInfo command_allocate = {
		.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
		.commandPool = command_pool,
		.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY, .commandBufferCount = 1,
	};
	TRY(vkAllocateCommandBuffers(device, &command_allocate, &command));
	VkCommandBufferBeginInfo begin = {
		.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
		.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT,
	};
	TRY(vkBeginCommandBuffer(command, &begin));
	VkBufferMemoryBarrier barrier = {
		.sType = VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER,
		.srcAccessMask = VK_ACCESS_HOST_WRITE_BIT,
		.dstAccessMask = VK_ACCESS_SHADER_WRITE_BIT,
		.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
		.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
		.buffer = buffer, .offset = 0, .size = buffer_info.size,
	};
	vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_HOST_BIT,
	    VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, 0, 0, NULL, 1, &barrier, 0, NULL);
	vkCmdBindPipeline(command, VK_PIPELINE_BIND_POINT_COMPUTE, pipeline);
	vkCmdBindDescriptorSets(command, VK_PIPELINE_BIND_POINT_COMPUTE,
	    pipeline_layout, 0, 1, &set, 0, NULL);
	vkCmdDispatch(command, WORDS, 1, 1);
	barrier.srcAccessMask = VK_ACCESS_SHADER_WRITE_BIT;
	barrier.dstAccessMask = VK_ACCESS_HOST_READ_BIT;
	vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
	    VK_PIPELINE_STAGE_HOST_BIT, 0, 0, NULL, 1, &barrier, 0, NULL);
	TRY(vkEndCommandBuffer(command));
	VkFenceCreateInfo fence_info = {
		.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO,
	};
	TRY(vkCreateFence(device, &fence_info, NULL, &fence));
	VkSubmitInfo submit = {
		.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO,
		.commandBufferCount = 1, .pCommandBuffers = &command,
	};
	result = vkQueueSubmit(queue, 1, &submit, fence);
	if (result != VK_SUCCESS) {
		fprintf(stderr, "Submission not accepted: %d; terminate without "
		    "destroying potentially active resources\n", result);
		return PENDING_EXIT;
	}
	result = vkWaitForFences(device, 1, &fence, VK_TRUE, WAIT_NS);
	if (result != VK_SUCCESS) {
		fprintf(stderr, "Fence not accepted: %d; terminate without "
		    "destroying potentially active resources\n", result);
		return PENDING_EXIT;
	}
	TRY(vkInvalidateMappedMemoryRanges(device, 1, &range));
	for (i = 0; i < WORDS; i++) {
		uint32_t actual = ((const uint32_t *)address)[i];
		if (actual != (VALUE ^ i)) {
			fprintf(stderr, "Readback[%u]: 0x%08" PRIx32
			    " expected 0x%08" PRIx32 "\n", i, actual, VALUE ^ i);
			goto out;
		}
	}
	puts("PASS: GPU compute wrote all 16 words; fence and host readback passed");
	status = 0;
out:
	if (fence != VK_NULL_HANDLE)
		vkDestroyFence(device, fence, NULL);
	if (command_pool != VK_NULL_HANDLE)
		vkDestroyCommandPool(device, command_pool, NULL);
	if (descriptor_pool != VK_NULL_HANDLE)
		vkDestroyDescriptorPool(device, descriptor_pool, NULL);
	if (pipeline != VK_NULL_HANDLE)
		vkDestroyPipeline(device, pipeline, NULL);
	if (shader != VK_NULL_HANDLE)
		vkDestroyShaderModule(device, shader, NULL);
	if (pipeline_layout != VK_NULL_HANDLE)
		vkDestroyPipelineLayout(device, pipeline_layout, NULL);
	if (set_layout != VK_NULL_HANDLE)
		vkDestroyDescriptorSetLayout(device, set_layout, NULL);
	if (mapped)
		vkUnmapMemory(device, memory);
	if (buffer != VK_NULL_HANDLE)
		vkDestroyBuffer(device, buffer, NULL);
	if (memory != VK_NULL_HANDLE)
		vkFreeMemory(device, memory, NULL);
	if (device != VK_NULL_HANDLE)
		vkDestroyDevice(device, NULL);
	if (instance != VK_NULL_HANDLE)
		vkDestroyInstance(instance, NULL);
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
	result = run_compute(st.st_rdev);
	if (result == PENDING_EXIT) {
		fflush(NULL);
		_Exit(result);
	}
	return result;
}
