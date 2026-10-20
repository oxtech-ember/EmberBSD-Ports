/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD allocation diagnostic (AI-assisted). */
#include <sys/types.h>
#include <sys/ioctl.h>

#include <drm.h>
#include <v3d_drm.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static const uint32_t single_sizes[] = {
	4096, 1048576, 4194304, 5246976, 7475200, 8388608, 16777216,
	16781312, 33554432
};
static const uint32_t held_sizes[] = { 5246976, 5246976, 7475200 };
_Static_assert(2U * 5246976U + 7475200U < 24U * 1048576U,
    "held allocation requests must remain below 24 MiB");

static bool
is_v3d(int fd)
{
	char name[16] = { 0 };
	struct drm_version version = {
		.name_len = sizeof(name) - 1,
		.name = name
	};
	int result, error;

	result = ioctl(fd, DRM_IOCTL_VERSION, &version);
	error = result < 0 ? errno : 0;
	name[sizeof(name) - 1] = '\0';
	printf("op=version ret=%d errno=%d driver=%s\n", result, error, name);
	return (result == 0 && version.name_len == 3 &&
	    memcmp(name, "v3d", 3) == 0);
}

static bool
create_bo(int fd, const char *phase, uint32_t size, uint32_t *handle)
{
	struct drm_v3d_create_bo create = { .size = size };
	int result, error;

	*handle = 0;
	result = ioctl(fd, DRM_IOCTL_V3D_CREATE_BO, &create);
	error = result < 0 ? errno : 0;
	printf("op=create phase=%s size=%" PRIu32 " ret=%d errno=%d"
	    " handle=%" PRIu32 "\n", phase, size, result, error,
	    result == 0 ? create.handle : 0);
	if (result != 0 || create.handle == 0)
		return (false);
	*handle = create.handle;
	return (true);
}

static bool
release_bo(int fd, const char *phase, uint32_t handle)
{
	struct drm_gem_close release = { .handle = handle };
	int result, error;

	result = ioctl(fd, DRM_IOCTL_GEM_CLOSE, &release);
	error = result < 0 ? errno : 0;
	printf("op=release phase=%s handle=%" PRIu32 " ret=%d errno=%d\n",
	    phase, handle, result, error);
	return (result == 0);
}

int
main(int argc, char **argv)
{
	uint32_t held[sizeof(held_sizes) / sizeof(held_sizes[0])] = { 0 };
	const char *node = "/dev/dri/renderD128";
	uint32_t handle;
	size_t i;
	unsigned int count = 0;
	int fd, result, error, failed = 0;

	if (argc > 2 || (argc == 2 && strcmp(argv[1], "--help") == 0)) {
		fprintf(stderr, "Usage: %s [RENDER_NODE]\n", argv[0]);
		return (argc > 2 ? 2 : 0);
	}
	if (argc == 2)
		node = argv[1];
	fd = open(node, O_RDWR | O_CLOEXEC);
	if (fd < 0) {
		error = errno;
		printf("op=open ret=-1 errno=%d node=%s\n", error, node);
		return (1);
	}
	printf("op=open ret=%d errno=0 node=%s\n", fd, node);
	if (!is_v3d(fd)) {
		failed = 1;
		goto out;
	}
	for (i = 0; i < sizeof(single_sizes) / sizeof(single_sizes[0]); i++) {
		if (!create_bo(fd, "single", single_sizes[i], &handle)) {
			failed = 1;
			continue;
		}
		if (!release_bo(fd, "single", handle)) {
			/* Stop allocation; descriptor teardown releases residual BOs. */
			failed = 1;
			goto out;
		}
	}
	for (i = 0; i < sizeof(held_sizes) / sizeof(held_sizes[0]); i++) {
		if (!create_bo(fd, "held", held_sizes[i], &held[count])) {
			failed = 1;
			break;
		}
		count++;
	}
	printf("op=held count=%u expected=3 requested_total=17969152\n", count);
	while (count != 0) {
		count--;
		if (!release_bo(fd, "held", held[count]))
			failed = 1;
	}
out:
	/* Never retry close: after EINTR, the descriptor may no longer be owned. */
	result = close(fd);
	error = result < 0 ? errno : 0;
	printf("op=close ret=%d errno=%d\n", result, error);
	if (result != 0 || fflush(stdout) != 0)
		failed = 1;
	return (failed);
}
