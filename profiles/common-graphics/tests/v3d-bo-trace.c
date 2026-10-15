/* SPDX-License-Identifier: BSD-2-Clause */
/* The resolver is the only test boundary. Execute the real tracing wrapper. */
#define dlsym test_dlsym
#include "../cross/v3d-bo-trace.c"
#undef dlsym

#include <stdlib.h>

static int provider_calls, resolver_calls, provider_mode;
static int expected_fd, expected_errno;
static unsigned long expected_request;
static void *expected_argument;

static int
provider(int fd, unsigned long request, void *argument)
{
	provider_calls++;
	if (fd != expected_fd || request != expected_request ||
	    argument != expected_argument || errno != expected_errno)
		abort();
	if (provider_mode == 1) {
		errno = ENOMEM;
		return (-1);
	}
	if (provider_mode == 2) {
		errno = EFAULT;
		return (-1);
	}
	if (provider_mode == 3) {
		errno = EBUSY;
		return (7);
	}
	if (request == DRM_IOCTL_V3D_CREATE_BO) {
		struct drm_v3d_create_bo *bo = argument;
		bo->size = 1; /* The trace must retain the caller's requested size. */
		bo->handle = 42;
		bo->offset = 4096;
	}
	return (0); /* Leave the incoming errno unchanged on success. */
}

void *
test_dlsym(void *handle, const char *symbol)
{
	drm_ioctl_fn function = provider;
	void *pointer;

	if (handle != RTLD_NEXT || strcmp(symbol, "drmIoctl") != 0)
		abort();
	resolver_calls++;
	errno = EINTR; /* Resolution must not leak its errno to the provider. */
	memcpy(&pointer, &function, sizeof(pointer));
	return (pointer);
}

static void
invoke(unsigned long request, void *argument, int mode, int result, int error)
{
	int previous = provider_calls;

	expected_fd = 37;
	expected_request = request;
	expected_argument = argument;
	expected_errno = ERANGE;
	provider_mode = mode;
	errno = expected_errno;
	if (drmIoctl(expected_fd, request, argument) != result ||
	    errno != error || provider_calls != previous + 1)
		abort();
}

int
main(int argc, char **argv)
{
	struct drm_v3d_create_bo create = { .size = 5242880, .flags = 3 };
	struct drm_gem_close close_bo = { .handle = 42 };
	char log[4096];
	int saved_stderr, capture[2], lines = 0;
	ssize_t length;
	bool valid_only = argc == 2 && strcmp(argv[1], "--valid-pointers-only") == 0;

	if (argc > 2 || (argc == 2 && !valid_only))
		return (2);
	saved_stderr = dup(STDERR_FILENO);
	if (saved_stderr < 0 || pipe(capture) < 0 ||
	    dup2(capture[1], STDERR_FILENO) < 0)
		abort();
	close(capture[1]);
	invoke(DRM_IOCTL_V3D_CREATE_BO, &create, 0, 0, ERANGE);
	if (create.size != 1 || create.handle != 42 || create.offset != 4096)
		abort();
	create.size = 67108864;
	invoke(DRM_IOCTL_V3D_CREATE_BO, &create, 1, -1, ENOMEM);
	invoke(DRM_IOCTL_GEM_CLOSE, &close_bo, 0, 0, ERANGE);
	invoke(0x1234, (void *)(uintptr_t)1, 3, 7, EBUSY);
	invoke(DRM_IOCTL_V3D_CREATE_BO, NULL, 2, -1, EFAULT);
	if (!valid_only)
		invoke(DRM_IOCTL_V3D_CREATE_BO, (void *)(uintptr_t)1, 2, -1, EFAULT);
	/* A log sink failure must not change a successful provider result. */
	close(STDERR_FILENO);
	invoke(DRM_IOCTL_GEM_CLOSE, &close_bo, 0, 0, ERANGE);
	if (dup2(saved_stderr, STDERR_FILENO) < 0)
		abort();
	close(saved_stderr);
	length = read(capture[0], log, sizeof(log) - 1);
	close(capture[0]);
	if (length < 0)
		abort();
	log[length] = 0;
	for (ssize_t i = 0; i < length; i++)
		if (log[i] == '\n')
			lines++;
	if (lines != (valid_only ? 4 : 5))
		abort();
	if (strstr(log, "op=create size=5242880 flags=3 input=readable ret=0") == NULL ||
	    strstr(log, "handle=42 output=readable") == NULL ||
	    strstr(log, "op=create size=67108864 flags=3 input=readable ret=-1") == NULL ||
	    strstr(log, "op=close handle=42 input=readable ret=0") == NULL ||
	    strstr(log, "input=unreadable ret=-1") == NULL || resolver_calls != 1)
		abort();
	fputs(log, stdout);
	printf("PASS forwarding, pointer identity, mutations, errno, log failure; calls=%d\n",
	    provider_calls);
	return (0);
}
