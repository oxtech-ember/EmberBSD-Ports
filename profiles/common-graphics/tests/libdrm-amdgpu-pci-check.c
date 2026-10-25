/* Origin: EmberBSD; AI-assisted installed libdrm checker regression. */
/* SPDX-License-Identifier: BSD-2-Clause */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int fixture_open(const char *, int, ...);
static int fixture_close(int);
static void fixture_free(void *);
#define open fixture_open
#define close fixture_close
#define free fixture_free
#define main production_check_main
#include "../cross/libdrm-platform-check.c"
#undef main
#undef free
#undef open
#undef close

enum fixture_mode {
	FIXTURE_AMDGPU,
	FIXTURE_V3D,
	FIXTURE_POWERVR
};

enum fixture_fault {
	FAULT_NONE,
	FAULT_OPEN,
	FAULT_VERSION,
	FAULT_WRONG_DRIVER,
	FAULT_NODE_TYPE,
	FAULT_NODE_TYPE_ERROR,
	FAULT_DEVICE,
	FAULT_WRONG_BUS,
	FAULT_WRONG_NODE_PATH,
	FAULT_WRONG_RENDER_NAME,
	FAULT_RENDER_NAME_ERROR,
	FAULT_ENUM_ERROR,
	FAULT_ENUM_ZERO,
	FAULT_ENUM_DUPLICATE,
	FAULT_NOT_EQUAL
};

#define TEST_FD 71
#define RENDER_NODE "/dev/dri/renderD128"

static enum fixture_mode current_mode;
static enum fixture_fault current_fault;
static drmDevice fake_device;
static drmVersion fake_version;
static drmPciBusInfo fake_pci_bus;
static drmPciDeviceInfo fake_pci_device;
static drmPlatformBusInfo fake_platform_bus;
static drmPlatformDeviceInfo fake_platform_device;
static char *fake_compatible[2];
static char *fake_nodes[DRM_NODE_MAX];
static char fake_driver[16];
static char fake_node_path[64];
static char fake_render_name[64];
static int open_calls;
static int successful_open_calls;
static int close_calls;
static int open_contract_ok;
static int version_allocations;
static int version_frees;
static int device_allocations;
static int device_frees;
static int render_name_allocations;
static int render_name_frees;
static int enumeration_allocations;
static int enumeration_frees;
static int enumeration_return_count;
static int enumeration_free_count;

static void
reset_fixture(enum fixture_mode mode, enum fixture_fault fault)
{
	current_mode = mode;
	current_fault = fault;
	memset(&fake_device, 0, sizeof(fake_device));
	memset(&fake_version, 0, sizeof(fake_version));
	memset(&fake_pci_bus, 0, sizeof(fake_pci_bus));
	memset(&fake_pci_device, 0, sizeof(fake_pci_device));
	memset(&fake_platform_bus, 0, sizeof(fake_platform_bus));
	memset(&fake_platform_device, 0, sizeof(fake_platform_device));
	memset(fake_nodes, 0, sizeof(fake_nodes));
	strcpy(fake_node_path, RENDER_NODE);
	strcpy(fake_render_name, RENDER_NODE);
	strcpy(fake_driver, mode == FIXTURE_AMDGPU ? "amdgpu" :
	    mode == FIXTURE_V3D ? "v3d" : "powervr");
	fake_nodes[DRM_NODE_RENDER] = fake_node_path;
	if (mode == FIXTURE_AMDGPU) {
		fake_device.bustype = DRM_BUS_PCI;
		fake_device.businfo.pci = &fake_pci_bus;
		fake_pci_device.vendor_id = 0x1234;
		fake_pci_device.device_id = 0x5678;
		fake_device.deviceinfo.pci = &fake_pci_device;
	} else {
		fake_device.bustype = DRM_BUS_PLATFORM;
		fake_device.businfo.platform = &fake_platform_bus;
		strcpy(fake_platform_bus.fullname, "test-gpu");
		fake_compatible[0] = mode == FIXTURE_V3D ? "acpi:BCM2850" :
		    "allwinner,sun60i-a733-gpu";
		fake_compatible[1] = NULL;
		fake_platform_device.compatible = fake_compatible;
		fake_device.deviceinfo.platform = &fake_platform_device;
	}
	fake_device.nodes = fake_nodes;
	fake_device.available_nodes = 1 << DRM_NODE_RENDER;
	fake_version.name = fake_driver;
	open_calls = 0;
	successful_open_calls = 0;
	close_calls = 0;
	open_contract_ok = 1;
	version_allocations = 0;
	version_frees = 0;
	device_allocations = 0;
	device_frees = 0;
	render_name_allocations = 0;
	render_name_frees = 0;
	enumeration_allocations = 0;
	enumeration_frees = 0;
	enumeration_return_count = 0;
	enumeration_free_count = 0;
	if (fault == FAULT_WRONG_BUS)
		fake_device.bustype = DRM_BUS_PLATFORM;
	if (fault == FAULT_WRONG_NODE_PATH)
		strcpy(fake_node_path, "/dev/dri/renderD127");
	if (fault == FAULT_WRONG_RENDER_NAME)
		strcpy(fake_render_name, "/dev/dri/renderD127");
}

static int
fixture_open(const char *path, int flags, ...)
{
	int expected_access;

	open_calls++;
	expected_access = current_mode == FIXTURE_AMDGPU ? O_RDONLY : O_RDWR;
	if (strcmp(path, RENDER_NODE) != 0 ||
	    (flags & O_ACCMODE) != expected_access || (flags & O_CLOEXEC) == 0)
		open_contract_ok = 0;
	if (current_fault == FAULT_OPEN) {
		errno = ENOENT;
		return -1;
	}
	successful_open_calls++;
	return TEST_FD;
}

static int
fixture_close(int fd)
{
	if (fd != TEST_FD)
		open_contract_ok = 0;
	close_calls++;
	return 0;
}

static void
fixture_free(void *ptr)
{
	if (ptr != NULL)
		render_name_frees++;
	free(ptr);
}

drmVersionPtr
drmGetVersion(int fd)
{
	if (fd != TEST_FD || current_fault == FAULT_VERSION)
		return NULL;
	if (current_fault == FAULT_WRONG_DRIVER)
		fake_version.name = "other";
	version_allocations++;
	return &fake_version;
}

void
drmFreeVersion(drmVersionPtr version)
{
	if (version != NULL)
		version_frees++;
}

int
drmGetNodeTypeFromFd(int fd)
{
	if (fd != TEST_FD || current_fault == FAULT_NODE_TYPE_ERROR)
		return -EIO;
	return current_fault == FAULT_NODE_TYPE ? DRM_NODE_PRIMARY : DRM_NODE_RENDER;
}

int
drmGetDevice2(int fd, uint32_t flags, drmDevicePtr *device)
{
	if (fd != TEST_FD || flags != 0 || current_fault == FAULT_DEVICE) {
		*device = NULL;
		return -EIO;
	}
	*device = &fake_device;
	device_allocations++;
	return 0;
}

char *
drmGetRenderDeviceNameFromFd(int fd)
{
	char *copy;
	const char *name;
	size_t length;

	if (fd != TEST_FD || current_fault == FAULT_RENDER_NAME_ERROR)
		return NULL;
	name = current_fault == FAULT_WRONG_RENDER_NAME ? fake_render_name :
	    fake_nodes[DRM_NODE_RENDER];
	length = strlen(name) + 1;
	copy = malloc(length);
	if (copy != NULL) {
		memcpy(copy, name, length);
		render_name_allocations++;
	}
	return copy;
}

int
drmGetDevices2(uint32_t flags, drmDevicePtr devices[], int max_devices)
{
	if (flags != 0 || max_devices != 64 || current_fault == FAULT_ENUM_ERROR)
		return -EIO;
	if (current_fault == FAULT_ENUM_ZERO)
		return 0;
	devices[0] = &fake_device;
	if (current_fault == FAULT_ENUM_DUPLICATE) {
		devices[1] = &fake_device;
		enumeration_allocations++;
		enumeration_return_count = 2;
		return 2;
	}
	enumeration_allocations++;
	enumeration_return_count = 1;
	return 1;
}

int
drmDevicesEqual(drmDevicePtr a, drmDevicePtr b)
{
	if (current_fault == FAULT_NOT_EQUAL)
		return 0;
	return a == b;
}

void
drmFreeDevices(drmDevicePtr devices[], int count)
{
	(void)devices;
	enumeration_frees++;
	enumeration_free_count = count;
}

void
drmFreeDevice(drmDevicePtr *device)
{
	if (*device != NULL)
		device_frees++;
	*device = NULL;
}

static int
run_case(const char *name, enum fixture_mode mode, enum fixture_fault fault,
    int argc, char **argv, int expected)
{
	int result;

	reset_fixture(mode, fault);
	if (expected != 0) {
		printf("CASE: %s expects rejection with status %d\n", name,
		    expected);
		(void)fflush(stdout);
	}
	result = production_check_main(argc, argv);
	if (result != expected || !open_contract_ok ||
	    successful_open_calls != close_calls ||
	    version_allocations != version_frees ||
	    device_allocations != device_frees ||
	    render_name_allocations != render_name_frees ||
	    enumeration_allocations != enumeration_frees ||
	    (enumeration_allocations != 0 &&
	    enumeration_return_count != enumeration_free_count) ||
	    (expected == 0 && (open_calls != 1 || close_calls != 1)) ||
	    (expected == 2 && open_calls != 0)) {
		fprintf(stderr, "FAIL: fixture %s result=%d expected=%d open=%d/%d "
		    "close=%d version=%d/%d device=%d/%d render=%d/%d "
		    "enum=%d/%d(%d/%d) flags=%d\n", name, result, expected,
		    successful_open_calls, open_calls, close_calls,
		    version_allocations, version_frees, device_allocations,
		    device_frees, render_name_allocations, render_name_frees,
		    enumeration_allocations, enumeration_frees,
		    enumeration_return_count, enumeration_free_count,
		    open_contract_ok);
		return 1;
	}
	printf("PASS: %s\n", name);
	return 0;
}

int
main(void)
{
	char *good[] = {
		"checker", "--amdgpu-pci", RENDER_NODE, "1234", "5678"
	};
	char *bad_vendor[] = {
		"checker", "--amdgpu-pci", RENDER_NODE, "1235", "5678"
	};
	char *bad_device[] = {
		"checker", "--amdgpu-pci", RENDER_NODE, "1234", "5679"
	};
	char *good_prefix[] = {
		"checker", "--amdgpu-pci", RENDER_NODE, "0x1234", "0X5678"
	};
	char *empty_id[] = {
		"checker", "--amdgpu-pci", RENDER_NODE, "", "5678"
	};
	char *empty_prefix[] = {
		"checker", "--amdgpu-pci", RENDER_NODE, "0x", "5678"
	};
	char *bad_hex[] = {
		"checker", "--amdgpu-pci", RENDER_NODE, "xyz", "5678"
	};
	char *bad_range[] = {
		"checker", "--amdgpu-pci", RENDER_NODE, "10000", "5678"
	};
	char *plus_id[] = {
		"checker", "--amdgpu-pci", RENDER_NODE, "+1234", "5678"
	};
	char *minus_id[] = {
		"checker", "--amdgpu-pci", RENDER_NODE, "-1234", "5678"
	};
	char *leading_space[] = {
		"checker", "--amdgpu-pci", RENDER_NODE, " 1234", "5678"
	};
	char *trailing_space[] = {
		"checker", "--amdgpu-pci", RENDER_NODE, "1234 ", "5678"
	};
	char *bad_device_hex[] = {
		"checker", "--amdgpu-pci", RENDER_NODE, "1234", "xyz"
	};
	char *empty_device[] = {
		"checker", "--amdgpu-pci", RENDER_NODE, "1234", ""
	};
	char *empty_device_prefix[] = {
		"checker", "--amdgpu-pci", RENDER_NODE, "1234", "0x"
	};
	char *bad_device_range[] = {
		"checker", "--amdgpu-pci", RENDER_NODE, "1234", "10000"
	};
	char *signed_device[] = {
		"checker", "--amdgpu-pci", RENDER_NODE, "1234", "+5678"
	};
	char *space_device[] = {
		"checker", "--amdgpu-pci", RENDER_NODE, "1234", " 5678"
	};
	char *old_v3d[] = { "checker", RENDER_NODE };
	char *old_powervr[] = {
		"checker", RENDER_NODE, "allwinner,sun60i-a733-gpu"
	};
#define CHECK(name, mode, fault, argc, argv, expected) \
	do { \
		if (run_case(name, mode, fault, argc, argv, expected) != 0) \
			return 1; \
	} while (0)
	CHECK("AMDGPU PCI identity", FIXTURE_AMDGPU, FAULT_NONE, 5, good, 0);
	CHECK("optional hexadecimal prefixes accepted", FIXTURE_AMDGPU,
	    FAULT_NONE, 5, good_prefix, 0);
	CHECK("vendor mismatch rejected", FIXTURE_AMDGPU, FAULT_NONE, 5,
	    bad_vendor, 1);
	CHECK("device mismatch rejected", FIXTURE_AMDGPU, FAULT_NONE, 5,
	    bad_device, 1);
	CHECK("empty PCI ID rejected before open", FIXTURE_AMDGPU, FAULT_NONE,
	    5, empty_id, 2);
	CHECK("empty hexadecimal prefix rejected before open", FIXTURE_AMDGPU,
	    FAULT_NONE, 5, empty_prefix, 2);
	CHECK("malformed PCI ID rejected before open", FIXTURE_AMDGPU,
	    FAULT_NONE, 5, bad_hex, 2);
	CHECK("out-of-range PCI ID rejected before open", FIXTURE_AMDGPU,
	    FAULT_NONE, 5, bad_range, 2);
	CHECK("signed PCI ID rejected before open", FIXTURE_AMDGPU, FAULT_NONE,
	    5, plus_id, 2);
	CHECK("negative PCI ID rejected before open", FIXTURE_AMDGPU, FAULT_NONE,
	    5, minus_id, 2);
	CHECK("leading whitespace rejected before open", FIXTURE_AMDGPU,
	    FAULT_NONE, 5, leading_space, 2);
	CHECK("trailing whitespace rejected before open", FIXTURE_AMDGPU,
	    FAULT_NONE, 5, trailing_space, 2);
	CHECK("malformed device ID rejected before open", FIXTURE_AMDGPU,
	    FAULT_NONE, 5, bad_device_hex, 2);
	CHECK("empty device ID rejected before open", FIXTURE_AMDGPU,
	    FAULT_NONE, 5, empty_device, 2);
	CHECK("empty device prefix rejected before open", FIXTURE_AMDGPU,
	    FAULT_NONE, 5, empty_device_prefix, 2);
	CHECK("out-of-range device ID rejected before open", FIXTURE_AMDGPU,
	    FAULT_NONE, 5, bad_device_range, 2);
	CHECK("signed device ID rejected before open", FIXTURE_AMDGPU,
	    FAULT_NONE, 5, signed_device, 2);
	CHECK("device ID whitespace rejected before open", FIXTURE_AMDGPU,
	    FAULT_NONE, 5, space_device, 2);
	CHECK("wrong driver rejected", FIXTURE_AMDGPU, FAULT_WRONG_DRIVER, 5, good, 1);
	CHECK("wrong node type rejected", FIXTURE_AMDGPU, FAULT_NODE_TYPE, 5, good, 1);
	CHECK("node-type API error rejected", FIXTURE_AMDGPU,
	    FAULT_NODE_TYPE_ERROR, 5, good, 1);
	CHECK("device API error rejected", FIXTURE_AMDGPU, FAULT_DEVICE, 5, good, 1);
	CHECK("wrong bus rejected", FIXTURE_AMDGPU, FAULT_WRONG_BUS, 5, good, 1);
	CHECK("node path mismatch rejected", FIXTURE_AMDGPU,
	    FAULT_WRONG_NODE_PATH, 5, good, 1);
	CHECK("render-name mismatch rejected", FIXTURE_AMDGPU,
	    FAULT_WRONG_RENDER_NAME, 5, good, 1);
	CHECK("render-name API error rejected", FIXTURE_AMDGPU,
	    FAULT_RENDER_NAME_ERROR, 5, good, 1);
	CHECK("zero enumeration rejected", FIXTURE_AMDGPU, FAULT_ENUM_ZERO,
	    5, good, 1);
	CHECK("duplicate enumeration rejected", FIXTURE_AMDGPU,
	    FAULT_ENUM_DUPLICATE, 5, good, 1);
	CHECK("device equality failure rejected", FIXTURE_AMDGPU,
	    FAULT_NOT_EQUAL, 5, good, 1);
	CHECK("enumeration API error rejected", FIXTURE_AMDGPU,
	    FAULT_ENUM_ERROR, 5, good, 1);
	CHECK("version API error rejected", FIXTURE_AMDGPU, FAULT_VERSION, 5, good, 1);
	CHECK("open error rejected", FIXTURE_AMDGPU, FAULT_OPEN, 5, good, 1);
	CHECK("existing V3D platform profile", FIXTURE_V3D, FAULT_NONE, 2, old_v3d, 0);
	CHECK("existing PowerVR platform profile", FIXTURE_POWERVR,
	    FAULT_NONE, 3, old_powervr, 0);
	puts("PASS: installed libdrm checker CLI fixtures");
	return 0;
}
