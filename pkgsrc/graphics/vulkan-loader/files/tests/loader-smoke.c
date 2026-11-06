/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <vulkan/vulkan.h>

int
main(void)
{
	void *loader = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
	PFN_vkGetInstanceProcAddr get_proc;
	PFN_vkEnumerateInstanceVersion get_version;
	uint32_t version = 0;

	if (loader == NULL) {
		fprintf(stderr, "dlopen: %s\n", dlerror());
		return 1;
	}
	get_proc = (PFN_vkGetInstanceProcAddr)dlsym(loader, "vkGetInstanceProcAddr");
	if (get_proc == NULL ||
	    (get_version = (PFN_vkEnumerateInstanceVersion)
	        get_proc(VK_NULL_HANDLE, "vkEnumerateInstanceVersion")) == NULL ||
	    get_version(&version) != VK_SUCCESS || VK_API_VERSION_MAJOR(version) != 1) {
		fputs("Vulkan loader entry point or version failed\n", stderr);
		dlclose(loader);
		return 1;
	}
	printf("Vulkan loader API %u.%u.%u\n", VK_API_VERSION_MAJOR(version),
	    VK_API_VERSION_MINOR(version), VK_API_VERSION_PATCH(version));
	dlclose(loader);
	return 0;
}
