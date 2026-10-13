/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). No device or queue creation. */
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

static bool
one_instance(dev_t expected)
{
	const VkApplicationInfo application = {
		.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
		.pApplicationName = "EmberBSD PowerVR enumeration check",
		.apiVersion = VK_API_VERSION_1_2,
	};
	const VkInstanceCreateInfo create = {
		.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
		.pApplicationInfo = &application,
	};
	VkInstance instance = VK_NULL_HANDLE;
	VkPhysicalDevice *devices = NULL;
	VkResult result;
	uint32_t count = 0, i, matches = 0;
	bool success = false;

	result = vkCreateInstance(&create, NULL, &instance);
	if (result != VK_SUCCESS) {
		fprintf(stderr, "vkCreateInstance: %d\n", result);
		return false;
	}
	result = vkEnumeratePhysicalDevices(instance, &count, NULL);
	if (result != VK_SUCCESS || count == 0 ||
	    (uint64_t)count * sizeof(*devices) > SIZE_MAX) {
		fprintf(stderr, "Physical device count: result=%d count=%u\n",
		    result, count);
		goto out;
	}
	devices = calloc(count, sizeof(*devices));
	if (devices == NULL)
		goto out;
	result = vkEnumeratePhysicalDevices(instance, &count, devices);
	if (result != VK_SUCCESS) {
		fprintf(stderr, "Physical device array: %d\n", result);
		goto out;
	}
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
		    drm.renderMinor != (int64_t)minor(expected))
			continue;
		if (properties.properties.apiVersion < VK_API_VERSION_1_2)
			goto out;
		matches++;
		printf("PowerVR: %s; driver=%s; Vulkan=%u.%u.%u; "
		    "render=%" PRId64 ":%" PRId64 "\n",
		    properties.properties.deviceName, driver.driverName,
		    VK_API_VERSION_MAJOR(properties.properties.apiVersion),
		    VK_API_VERSION_MINOR(properties.properties.apiVersion),
		    VK_API_VERSION_PATCH(properties.properties.apiVersion),
		    drm.renderMajor, drm.renderMinor);
	}
	success = matches == 1;
	if (!success)
		fprintf(stderr, "Expected one matching PowerVR device, got %u\n",
		    matches);
out:
	free(devices);
	vkDestroyInstance(instance, NULL);
	return success;
}

int
main(int argc, char **argv)
{
	struct stat st;
	unsigned int i;

	if (argc != 2) {
		fprintf(stderr, "Usage: %s RENDER_NODE\n", argv[0]);
		return 2;
	}
	if (stat(argv[1], &st) != 0 || !S_ISCHR(st.st_mode)) {
		fprintf(stderr, "Not a character device: %s\n", argv[1]);
		return 1;
	}
	for (i = 0; i < 4; i++) {
		if (!one_instance(st.st_rdev))
			return 1;
	}
	puts("PASS: four installed PowerVR enumeration lifecycles; no GPU submission");
	return 0;
}
