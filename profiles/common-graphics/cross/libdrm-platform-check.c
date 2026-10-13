/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD; AI-assisted installed platform identity acceptance. */
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <xf86drm.h>

#define REQUIRE(x) do { if (!(x)) { fprintf(stderr, "FAIL: %s\n", #x); return 1; } } while (0)

int
main(int argc, char **argv)
{
	drmDevicePtr device = NULL, devices[64] = { 0 };
	drmVersionPtr version;
	const char *compatible, *driver;
	char *render;
	int fd, count, found = 0;

	if (argc != 2 && argc != 3) {
		fprintf(stderr, "usage: %s render-node [expected-compatible]\n", argv[0]);
		return 2;
	}
	compatible = argc == 3 ? argv[2] : "acpi:BCM2850";
	if (strcmp(compatible, "acpi:BCM2850") == 0)
		driver = "v3d";
	else if (strcmp(compatible, "allwinner,sun60i-a733-gpu") == 0)
		driver = "powervr";
	else {
		fprintf(stderr, "unsupported expected-compatible: %s\n", compatible);
		return 2;
	}
	fd = open(argv[1], O_RDWR | O_CLOEXEC);
	REQUIRE(fd >= 0);
	version = drmGetVersion(fd);
	REQUIRE(version != NULL && strcmp(version->name, driver) == 0);
	drmFreeVersion(version);
	REQUIRE(drmGetNodeTypeFromFd(fd) == DRM_NODE_RENDER);
	REQUIRE(drmGetDevice2(fd, 0, &device) == 0);
	REQUIRE(device->bustype == DRM_BUS_PLATFORM);
	REQUIRE(device->available_nodes & (1 << DRM_NODE_RENDER));
	REQUIRE(strcmp(device->nodes[DRM_NODE_RENDER], argv[1]) == 0);
	REQUIRE(strcmp(device->deviceinfo.platform->compatible[0], compatible) == 0);
	render = drmGetRenderDeviceNameFromFd(fd);
	REQUIRE(render != NULL && strcmp(render, argv[1]) == 0);
	free(render);
	count = drmGetDevices2(0, devices, 64);
	REQUIRE(count > 0 && count <= 64);
	for (int i = 0; i < count; i++)
		if (drmDevicesEqual(device, devices[i]))
			found++;
	REQUIRE(found == 1);
	printf("PASS: installed libdrm platform=%s compatible=%s render=%s; "
	    "enumeration, node type and folding; uid=%lu\n",
	    device->businfo.platform->fullname,
	    device->deviceinfo.platform->compatible[0], device->nodes[DRM_NODE_RENDER],
	    (unsigned long)getuid());
	drmFreeDevices(devices, count);
	drmFreeDevice(&device);
	REQUIRE(close(fd) == 0);
	return 0;
}
