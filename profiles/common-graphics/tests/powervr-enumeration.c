/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). Actual consumer error paths. */
#include <sys/types.h>
#include <sys/stat.h>
#include <vulkan/vulkan.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks, creates, destroys, live, properties_calls;
static int scenario;
#define CHECK(c) do { checks++; if (!(c)) { \
    fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #c); abort(); } } while (0)

VKAPI_ATTR VkResult VKAPI_CALL
vkCreateInstance(const VkInstanceCreateInfo *info,
    const VkAllocationCallbacks *alloc, VkInstance *instance)
{
	CHECK(info->pApplicationInfo->apiVersion == VK_API_VERSION_1_2);
	CHECK(alloc == NULL && live == 0);
	creates++;
	if (scenario == 1)
		return VK_ERROR_INCOMPATIBLE_DRIVER;
	*instance = (VkInstance)(uintptr_t)1;
	live++;
	return VK_SUCCESS;
}

VKAPI_ATTR void VKAPI_CALL
vkDestroyInstance(VkInstance instance, const VkAllocationCallbacks *alloc)
{
	CHECK(instance == (VkInstance)(uintptr_t)1 && alloc == NULL && live == 1);
	live--;
	destroys++;
}

VKAPI_ATTR VkResult VKAPI_CALL
vkEnumeratePhysicalDevices(VkInstance instance, uint32_t *count,
    VkPhysicalDevice *devices)
{
	CHECK(instance == (VkInstance)(uintptr_t)1 && live == 1);
	if (devices == NULL) {
		*count = scenario == 2 ? 0 : (scenario == 6 ? 2 : 1);
		return scenario == 3 ? VK_ERROR_OUT_OF_HOST_MEMORY : VK_SUCCESS;
	}
	CHECK(*count == (scenario == 6 ? 2U : 1U));
	for (uint32_t i = 0; i < *count; i++)
		devices[i] = (VkPhysicalDevice)(uintptr_t)(i + 10);
	return scenario == 4 ? VK_INCOMPLETE : VK_SUCCESS;
}

VKAPI_ATTR VkResult VKAPI_CALL
vkEnumerateDeviceExtensionProperties(VkPhysicalDevice device, const char *layer,
    uint32_t *count, VkExtensionProperties *properties)
{
	CHECK((uintptr_t)device >= 10 && layer == NULL);
	if (properties == NULL) {
		*count = scenario == 10 ? 0 : 1;
		return scenario == 9 ? VK_ERROR_OUT_OF_HOST_MEMORY : VK_SUCCESS;
	}
	CHECK(*count == 1);
	strcpy(properties[0].extensionName, scenario == 5 ? "VK_test_absent" :
	    VK_EXT_PHYSICAL_DEVICE_DRM_EXTENSION_NAME);
	return scenario == 11 ? VK_INCOMPLETE : VK_SUCCESS;
}

VKAPI_ATTR void VKAPI_CALL
vkGetPhysicalDeviceProperties2(VkPhysicalDevice device,
    VkPhysicalDeviceProperties2 *properties)
{
	VkPhysicalDeviceDriverProperties *driver = properties->pNext;
	VkPhysicalDeviceDrmPropertiesEXT *drm = driver->pNext;

	CHECK((uintptr_t)device >= 10);
	CHECK(properties->sType == VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2);
	CHECK(driver->sType == VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DRIVER_PROPERTIES);
	CHECK(drm->sType == VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DRM_PROPERTIES_EXT);
	properties_calls++;
	properties->properties.vendorID = scenario == 7 ? 0 : 0x1010;
	properties->properties.apiVersion = scenario == 12 ? VK_API_VERSION_1_1 : VK_API_VERSION_1_2;
	strcpy(properties->properties.deviceName, "PowerVR fixture");
	driver->driverID = scenario == 13 ? VK_DRIVER_ID_MESA_LLVMPIPE : VK_DRIVER_ID_IMAGINATION_OPEN_SOURCE_MESA;
	strcpy(driver->driverName, "powervr");
	drm->hasRender = scenario != 14;
	drm->renderMajor = 0;
	drm->renderMinor = scenario == 8 ? 1 : 0;
}

#define main consumer_main
#include "powervr-enumerate.c"
#undef main

int
main(void)
{
	for (scenario = 0; scenario <= 14; scenario++) {
		unsigned before_create = creates, before_destroy = destroys;
		bool result = one_instance(0);
		CHECK(result == (scenario == 0));
		CHECK(creates == before_create + 1);
		CHECK(destroys == before_destroy + (scenario == 1 ? 0 : 1));
		CHECK(live == 0);
	}
	scenario = 0;
	for (unsigned i = 0; i < 4; i++)
		CHECK(one_instance(0));
	CHECK(live == 0 && properties_calls > 4);
	printf("PASS: %u actual enumeration consumer checks; Vulkan calls are modelled\n", checks);
	return 0;
}
