/* SPDX-License-Identifier: BSD-2-Clause */
/* Copyright (c) 2026 EmberBSD contributors. */
/* Origin: EmberBSD bounded Vulkan transfer diagnostic, AI-assisted. */
#include <vulkan/vulkan.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(call)                                                            \
	do {                                                                   \
		VkResult result_ = (call);                                     \
		if (result_ != VK_SUCCESS) {                                   \
			fprintf(stderr, "%s: VkResult %d\n", #call, result_);  \
			return 1;                                              \
		}                                                              \
	} while (0)

int
main(int argc, char **argv)
{
	bool is_fill = false, cached = false;
	if (argc < 3 || argc > 5) {
		fprintf(
		    stderr, "usage: copy-buffer BYTES CHUNK_BYTES [--fill] [--cached]\n");
		return 2;
	}
	for (int i = 3; i < argc; i++) {
		if (strcmp(argv[i], "--fill") == 0 && !is_fill)
			is_fill = true;
		else if (strcmp(argv[i], "--cached") == 0 && !cached)
			cached = true;
		else
			return 2;
	}
	char *end;
	unsigned long bytes = strtoul(argv[1], &end, 10);
	if (*end || !bytes || bytes > 192 || bytes % 4)
		return 2;
	unsigned long chunk = strtoul(argv[2], &end, 10);
	if (*end || !chunk || chunk > bytes || chunk % 4)
		return 2;

	VkApplicationInfo application = {
	    .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
	    .pApplicationName = "Ember transfer probe",
	    .apiVersion = VK_API_VERSION_1_0,
	};
	VkInstanceCreateInfo ici = {
	    .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
	    .pApplicationInfo = &application,
	};
	VkInstance instance;
	CHECK(vkCreateInstance(&ici, NULL, &instance));
	uint32_t count = 16;
	VkPhysicalDevice devices[16], physical = VK_NULL_HANDLE;
	CHECK(vkEnumeratePhysicalDevices(instance, &count, devices));
	for (uint32_t i = 0; i < count; i++) {
		VkPhysicalDeviceProperties properties;
		vkGetPhysicalDeviceProperties(devices[i], &properties);
		if (properties.vendorID == 0x1010 &&
		    strstr(properties.deviceName, "GE8300")) {
			physical = devices[i];
			printf("GPU %s\n", properties.deviceName);
			break;
		}
	}
	if (!physical)
		return 1;
	VkQueueFamilyProperties families[16];
	count = 16;
	vkGetPhysicalDeviceQueueFamilyProperties(physical, &count, families);
	uint32_t family;
	for (family = 0; family < count; family++)
		if (families[family].queueCount &&
		    (families[family].queueFlags & VK_QUEUE_TRANSFER_BIT))
			break;
	if (family == count)
		return 1;
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
	VkBuffer buffers[2];
	VkDeviceMemory memory[2];
	unsigned char *mapped[2];
	for (unsigned i = 0; i < 2; i++) {
		VkBufferCreateInfo bci = {
		    .sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
		    .size = 256,
		    .usage = VK_BUFFER_USAGE_TRANSFER_SRC_BIT |
			VK_BUFFER_USAGE_TRANSFER_DST_BIT,
		    .sharingMode = VK_SHARING_MODE_EXCLUSIVE,
		};
		CHECK(vkCreateBuffer(device, &bci, NULL, &buffers[i]));
		VkMemoryRequirements requirements;
		vkGetBufferMemoryRequirements(
		    device, buffers[i], &requirements);
		const VkMemoryPropertyFlags required =
		    VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
		    (cached ? VK_MEMORY_PROPERTY_HOST_CACHED_BIT :
		    VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
		uint32_t type;
		for (type = 0; type < memory_properties.memoryTypeCount; type++)
			if ((requirements.memoryTypeBits & (1U << type)) &&
			    (memory_properties.memoryTypes[type].propertyFlags &
				required) == required)
				break;
		if (type == memory_properties.memoryTypeCount)
			return 1;
		VkMemoryAllocateInfo mai = {
		    .sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
		    .allocationSize = requirements.size,
		    .memoryTypeIndex = type,
		};
		CHECK(vkAllocateMemory(device, &mai, NULL, &memory[i]));
		CHECK(vkBindBufferMemory(device, buffers[i], memory[i], 0));
		void *address;
		CHECK(vkMapMemory(
		    device, memory[i], 0, VK_WHOLE_SIZE, 0, &address));
		mapped[i] = address;
		printf("buffer %u memory type %u flags %#x\n", i, type,
		    memory_properties.memoryTypes[type].propertyFlags);
	}
	for (unsigned i = 0; i < 256; i++) {
		mapped[0][i] = (unsigned char)(i * 13U + 7U);
		mapped[1][i] = 0xa5;
	}
	VkMappedMemoryRange ranges[2];
	for (unsigned i = 0; i < 2; i++)
		ranges[i] = (VkMappedMemoryRange){
		    .sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE,
		    .memory = memory[i], .offset = 0, .size = VK_WHOLE_SIZE,
		};
	if (cached)
		CHECK(vkFlushMappedMemoryRanges(device, 2, ranges));
	VkCommandPoolCreateInfo pci = {
	    .sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
	    .queueFamilyIndex = family,
	};
	VkCommandPool pool;
	CHECK(vkCreateCommandPool(device, &pci, NULL, &pool));
	VkCommandBufferAllocateInfo cai = {
	    .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
	    .commandPool = pool,
	    .level = VK_COMMAND_BUFFER_LEVEL_PRIMARY,
	    .commandBufferCount = 1,
	};
	VkCommandBuffer commands;
	CHECK(vkAllocateCommandBuffers(device, &cai, &commands));
	VkCommandBufferBeginInfo begin = {
	    .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
	    .flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT,
	};
	CHECK(vkBeginCommandBuffer(commands, &begin));
	VkMemoryBarrier before = {
	    .sType = VK_STRUCTURE_TYPE_MEMORY_BARRIER,
	    .srcAccessMask = VK_ACCESS_HOST_WRITE_BIT,
	    .dstAccessMask = VK_ACCESS_TRANSFER_READ_BIT,
	};
	vkCmdPipelineBarrier(commands, VK_PIPELINE_STAGE_HOST_BIT,
	    VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 1, &before, 0, NULL, 0, NULL);
	unsigned copies = 0;
	for (unsigned long offset = 0; offset < bytes; offset += chunk) {
		VkBufferCopy region = {
		    .srcOffset = 16 + offset,
		    .dstOffset = 16 + offset,
		    .size = bytes - offset < chunk ? bytes - offset : chunk,
		};
		if (is_fill)
			vkCmdFillBuffer(commands, buffers[1], region.dstOffset,
			    region.size, 0x13579bdf);
		else
			vkCmdCopyBuffer(
			    commands, buffers[0], buffers[1], 1, &region);
		copies++;
	}
	VkMemoryBarrier after = {
	    .sType = VK_STRUCTURE_TYPE_MEMORY_BARRIER,
	    .srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT,
	    .dstAccessMask = VK_ACCESS_HOST_READ_BIT,
	};
	vkCmdPipelineBarrier(commands, VK_PIPELINE_STAGE_TRANSFER_BIT,
	    VK_PIPELINE_STAGE_HOST_BIT, 0, 1, &after, 0, NULL, 0, NULL);
	CHECK(vkEndCommandBuffer(commands));
	VkFenceCreateInfo fci = {.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
	VkFence fence;
	CHECK(vkCreateFence(device, &fci, NULL, &fence));
	VkSubmitInfo submit = {
	    .sType = VK_STRUCTURE_TYPE_SUBMIT_INFO,
	    .commandBufferCount = 1,
	    .pCommandBuffers = &commands,
	};
	printf("%s bytes=%lu chunk=%lu commands=%u\n",
	    is_fill ? "FILL" : "COPY", bytes, chunk, copies);
	fflush(stdout);
	CHECK(vkQueueSubmit(queue, 1, &submit, fence));
	CHECK(
	    vkWaitForFences(device, 1, &fence, VK_TRUE, UINT64_C(5000000000)));
	if (cached)
		CHECK(vkInvalidateMappedMemoryRanges(device, 2, ranges));
	const uint32_t fill_word = 0x13579bdf;
	unsigned char fill_bytes[4];
	memcpy(fill_bytes, &fill_word, sizeof(fill_word));
	for (unsigned i = 0; i < 256; i++) {
		unsigned char expected = 0xa5;
		if (i >= 16 && i < 16 + bytes)
			expected = is_fill ? fill_bytes[(i - 16) % 4]
					   : (unsigned char)(i * 13U + 7U);
		if (mapped[1][i] != expected ||
		    mapped[0][i] != (unsigned char)(i * 13U + 7U)) {
			fprintf(stderr,
			    "byte mismatch %u: dst=%02x expected=%02x "
			    "src=%02x\n",
			    i, mapped[1][i], expected, mapped[0][i]);
			return 1;
		}
	}
	vkDestroyFence(device, fence, NULL);
	vkDestroyCommandPool(device, pool, NULL);
	for (unsigned i = 0; i < 2; i++) {
		vkUnmapMemory(device, memory[i]);
		vkDestroyBuffer(device, buffers[i], NULL);
		vkFreeMemory(device, memory[i], NULL);
	}
	vkDestroyDevice(device, NULL);
	vkDestroyInstance(instance, NULL);
	puts("PASS: exact transfer; source and destination guards intact");
	return 0;
}
