/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD; AI-assisted installed DRM identity acceptance. */
#include <sys/types.h>
#include <sys/stat.h>
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <xf86drm.h>

#define REQUIRE(x) do { if (!(x)) { fprintf(stderr, "FAIL: %s\n", #x); return 1; } } while (0)
#define PCI_REQUIRE(x) do { if (!(x)) { \
	fprintf(stderr, "FAIL: %s\n", #x); \
	goto cleanup; \
} } while (0)

static int
parse_pci_id(const char *text, uint16_t *id)
{
	const char *digits = text;
	const char *p;
	char *end;
	unsigned long value;

	if (digits[0] == '0' && (digits[1] == 'x' || digits[1] == 'X'))
		digits += 2;
	if (*digits == '\0')
		return 0;
	for (p = digits; *p != '\0'; p++)
		if (!isxdigit((unsigned char)*p))
			return 0;
	errno = 0;
	value = strtoul(digits, &end, 16);
	if (errno == ERANGE || end == digits || *end != '\0' ||
	    value > UINT16_MAX)
		return 0;
	*id = (uint16_t)value;
	return 1;
}

static int
check_amdgpu_pci(const char *render_node, uint16_t expected_vendor,
    uint16_t expected_device)
{
	drmDevicePtr device = NULL, devices[64] = { 0 };
	drmVersionPtr version = NULL;
	char *render = NULL;
	int fd = -1, count = 0, free_count = 0, found = 0, result = 1;

	fd = open(render_node, O_RDONLY | O_CLOEXEC);
	PCI_REQUIRE(fd >= 0);
	version = drmGetVersion(fd);
	PCI_REQUIRE(version != NULL);
	PCI_REQUIRE(version->name != NULL && strcmp(version->name, "amdgpu") == 0);
	drmFreeVersion(version);
	version = NULL;
	PCI_REQUIRE(drmGetNodeTypeFromFd(fd) == DRM_NODE_RENDER);
	PCI_REQUIRE(drmGetDevice2(fd, 0, &device) == 0);
	PCI_REQUIRE(device != NULL);
	PCI_REQUIRE(device->bustype == DRM_BUS_PCI);
	PCI_REQUIRE(device->deviceinfo.pci != NULL);
	PCI_REQUIRE(device->deviceinfo.pci->vendor_id == expected_vendor);
	PCI_REQUIRE(device->deviceinfo.pci->device_id == expected_device);
	PCI_REQUIRE(device->available_nodes & (1 << DRM_NODE_RENDER));
	PCI_REQUIRE(device->nodes != NULL && device->nodes[DRM_NODE_RENDER] != NULL);
	PCI_REQUIRE(strcmp(device->nodes[DRM_NODE_RENDER], render_node) == 0);
	render = drmGetRenderDeviceNameFromFd(fd);
	PCI_REQUIRE(render != NULL && strcmp(render, render_node) == 0);
	free(render);
	render = NULL;
	count = drmGetDevices2(0, devices, 64);
	if (count > 0)
		free_count = count > 64 ? 64 : count;
	PCI_REQUIRE(count > 0 && count <= 64);
	for (int i = 0; i < count; i++)
		if (devices[i] != NULL && drmDevicesEqual(device, devices[i]))
			found++;
	PCI_REQUIRE(found == 1);
	result = 0;

cleanup:
	if (render != NULL)
		free(render);
	if (count > 0)
		drmFreeDevices(devices, free_count);
	if (device != NULL)
		drmFreeDevice(&device);
	if (version != NULL)
		drmFreeVersion(version);
	if (fd >= 0 && close(fd) != 0) {
		fprintf(stderr, "FAIL: close(render node)\n");
		result = 1;
	}
	if (result == 0)
		printf("PASS: installed libdrm amdgpu PCI=%04x:%04x render=%s; "
		    "driver, node type, enumeration, equality and name; uid=%lu\n",
		    expected_vendor, expected_device, render_node,
		    (unsigned long)getuid());
	return result;
}

int
main(int argc, char **argv)
{
	drmDevicePtr device = NULL, devices[64] = { 0 };
	drmVersionPtr version;
	const char *compatible, *driver;
	char *render;
	uint16_t vendor_id, device_id;
	int fd, count, found = 0;

	if (argc > 1 && strcmp(argv[1], "--amdgpu-pci") == 0) {
		if (argc != 5) {
			fprintf(stderr, "usage: %s --amdgpu-pci render-node "
			    "vendor-id-hex device-id-hex\n", argv[0]);
			return 2;
		}
		if (!parse_pci_id(argv[3], &vendor_id) ||
		    !parse_pci_id(argv[4], &device_id)) {
			fprintf(stderr, "invalid PCI ID; expected a 16-bit hexadecimal value\n");
			return 2;
		}
		return check_amdgpu_pci(argv[2], vendor_id, device_id);
	}
	if (argc != 2 && argc != 3) {
		fprintf(stderr, "usage: %s render-node [expected-compatible]\n"
		    "       %s --amdgpu-pci render-node vendor-id-hex device-id-hex\n",
		    argv[0], argv[0]);
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
