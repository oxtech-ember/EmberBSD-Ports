/* SPDX-License-Identifier: BSD-2-Clause */
/* Opt-in, process-local tracing of the public libdrm drmIoctl function. */
#define _GNU_SOURCE
#include <sys/types.h>

#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include <xf86drm.h>
#include <v3d_drm.h>

typedef int (*drm_ioctl_fn)(int, unsigned long, void *);
static drm_ioctl_fn next_ioctl;
static pthread_once_t resolve_once = PTHREAD_ONCE_INIT;

static void
resolve_ioctl(void)
{
	void *symbol;

	symbol = dlsym(RTLD_NEXT, "drmIoctl");
	if (symbol == NULL) {
		static const char message[] =
		    "ember-v3d-bo: cannot resolve next drmIoctl; trace cannot run\n";
		(void)write(STDERR_FILENO, message, sizeof(message) - 1);
		_exit(125);
	}
	_Static_assert(sizeof(symbol) == sizeof(next_ioctl), "POSIX dlsym pointer size");
	memcpy(&next_ioctl, &symbol, sizeof(next_ioctl));
}

/* Kernel-mediated copying preserves EFAULT behavior for inaccessible pointers. */
static bool
snapshot(void *destination, const void *source, size_t length)
{
	int fds[2];
	ssize_t count = -1;

	if (source == NULL)
		return (false);
#if defined(__NetBSD__) || defined(__linux__)
	if (pipe2(fds, O_CLOEXEC) < 0)
		return (false);
#else
	if (pipe(fds) < 0)
		return (false);
	if (fcntl(fds[0], F_SETFD, FD_CLOEXEC) < 0 ||
	    fcntl(fds[1], F_SETFD, FD_CLOEXEC) < 0)
		goto out;
#endif
	/* Both UAPI structures are smaller than PIPE_BUF. The pipe is empty. */
	if (write(fds[1], source, length) == (ssize_t)length)
		count = read(fds[0], destination, length);
#if !defined(__NetBSD__) && !defined(__linux__)
out:
#endif
	(void)close(fds[0]);
	(void)close(fds[1]);
	return (count == (ssize_t)length);
}

int
drmIoctl(int fd, unsigned long request, void *argument)
{
	struct drm_v3d_create_bo before = { 0 }, after = { 0 };
	struct drm_gem_close close_bo = { 0 };
	int entry_errno = errno, result, result_errno, length;
	bool readable = false, output_readable = false;
	char line[256];

	(void)pthread_once(&resolve_once, resolve_ioctl);
	if (request == DRM_IOCTL_V3D_CREATE_BO)
		readable = snapshot(&before, argument, sizeof(before));
	else if (request == DRM_IOCTL_GEM_CLOSE)
		readable = snapshot(&close_bo, argument, sizeof(close_bo));

	errno = entry_errno;
	result = next_ioctl(fd, request, argument);
	result_errno = errno;

	if (request == DRM_IOCTL_V3D_CREATE_BO) {
		if (result == 0)
			output_readable = snapshot(&after, argument, sizeof(after));
		length = snprintf(line, sizeof(line),
		    "ember-v3d-bo pid=%ld fd=%d op=create size=%" PRIu32
		    " flags=%" PRIu32 " input=%s ret=%d errno=%d handle=%" PRIu32
		    " output=%s\n", (long)getpid(), fd, before.size, before.flags,
		    readable ? "readable" : "unreadable", result, result_errno,
		    after.handle, output_readable ? "readable" : "unavailable");
	} else if (request == DRM_IOCTL_GEM_CLOSE) {
		length = snprintf(line, sizeof(line),
		    "ember-v3d-bo pid=%ld fd=%d op=close handle=%" PRIu32
		    " input=%s ret=%d errno=%d\n", (long)getpid(), fd,
		    close_bo.handle, readable ? "readable" : "unreadable",
		    result, result_errno);
	} else {
		errno = result_errno;
		return (result);
	}
	if (length > 0 && (size_t)length < sizeof(line))
		(void)write(STDERR_FILENO, line, (size_t)length);
	errno = result_errno;
	return (result);
}
