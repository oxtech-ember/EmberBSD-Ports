/* SPDX-License-Identifier: BSD-2-Clause */
/* Execute the production CLI with only system-call adapters replaced. */
#include <sys/types.h>
#include <sys/ioctl.h>
#include <drm.h>
#include <v3d_drm.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int v3d_bo_alloc_main(int, char **);
int test_open(const char *, int, ...);
int test_ioctl(int, unsigned long, ...);
int test_close(int);

#define CHECK(c) do { if (!(c)) { \
	fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #c); exit(1); \
} } while (0)

static const uint32_t sizes[] = {
	4096, 1048576, 4194304, 5246976, 7475200, 8388608, 16777216,
	5246976, 5246976, 7475200
};
static uint32_t live[11], live_bytes, peak_bytes;
static unsigned creates, releases, opened, closed, versions;
static int fail_create, fail_release, fail_errno;
static bool fail_open, fail_version, wrong_driver, zero_handle, fail_close;
static FILE *capture;
static int capture_fd;

int
test_open(const char *path, int flags, ...)
{
	CHECK(strcmp(path, "/dev/dri/renderD128") == 0);
	CHECK(flags == (O_RDWR | O_CLOEXEC));
	opened++;
	if (fail_open) {
		errno = EACCES;
		return (-1);
	}
	return (42);
}

int
test_ioctl(int fd, unsigned long request, ...)
{
	struct drm_v3d_create_bo *create;
	const struct drm_gem_close *release;
	void *argument;
	va_list ap;

	CHECK(fd == 42 && closed == 0 && !fail_open);
	va_start(ap, request);
	argument = va_arg(ap, void *);
	va_end(ap);
	if (request == DRM_IOCTL_VERSION) {
		struct drm_version *version = argument;

		versions++;
		CHECK(version->name_len >= 4);
		if (fail_version) {
			errno = ENOTTY;
			return (-1);
		}
		memcpy(version->name, wrong_driver ? "foo" : "v3d", 3);
		version->name_len = 3;
		return (0);
	}
	CHECK(versions == 1 && !wrong_driver && !fail_version);
	if (request == DRM_IOCTL_V3D_CREATE_BO) {
		create = argument;
		CHECK(creates < 10);
		CHECK(create->size == sizes[creates]);
		CHECK(create->flags == 0 && create->handle == 0 && create->offset == 0);
		creates++;
		if ((int)creates == fail_create) {
			/* Failed output fields are not owned handles. */
			create->handle = 0xdead;
			errno = fail_errno;
			return (-1);
		}
		if (zero_handle && creates == 1)
			return (0);
		create->handle = creates;
		live[creates] = create->size;
		live_bytes += create->size;
		if (live_bytes > peak_bytes)
			peak_bytes = live_bytes;
		CHECK(live_bytes < 24U * 1048576U);
		errno = EBUSY; /* Success must not print stale errno. */
		return (0);
	}
	CHECK(request == DRM_IOCTL_GEM_CLOSE);
	release = argument;
	CHECK(release->handle > 0 && release->handle <= 10);
	CHECK(live[release->handle] != 0 && release->pad == 0);
	releases++;
	if ((int)releases == fail_release) {
		errno = fail_errno;
		return (-1);
	}
	live_bytes -= live[release->handle];
	live[release->handle] = 0;
	return (0);
}

int
test_close(int fd)
{
	CHECK(fd == 42 && closed == 0 && !fail_open);
	closed++;
	/* Kernel file teardown owns any BO whose explicit GEM_CLOSE failed. */
	memset(live, 0, sizeof(live));
	live_bytes = 0;
	if (fail_close) {
		errno = EINTR;
		return (-1);
	}
	return (0);
}

static void
reset(void)
{
	memset(live, 0, sizeof(live));
	live_bytes = peak_bytes = 0;
	creates = releases = opened = closed = versions = 0;
	fail_create = fail_release = 0;
	fail_errno = ENOMEM;
	fail_open = fail_version = wrong_driver = zero_handle = fail_close = false;
	rewind(capture);
	CHECK(ftruncate(capture_fd, 0) == 0);
}

static void
run(int expected)
{
	char *args[] = { (char *)"v3d-bo-alloc", NULL };
	char text[4096];
	size_t length;
	int result;

	result = v3d_bo_alloc_main(1, args);
	CHECK(result == expected);
	CHECK(opened == 1 && closed == (fail_open ? 0U : 1U));
	CHECK(live_bytes == 0);
	CHECK(fflush(stdout) == 0);
	rewind(capture);
	length = fread(text, 1, sizeof(text) - 1, capture);
	text[length] = '\0';
	CHECK(strstr(text, "errno=16") == NULL); /* stale EBUSY */
	if (fail_create != 0 && fail_errno == ENOMEM)
		CHECK(strstr(text, "ret=-1 errno=12 handle=0") != NULL);
}

int
main(void)
{
	unsigned i, tests = 0;
	int saved_stdout, unreadable, result;
	char *args[] = { (char *)"v3d-bo-alloc", NULL };

	capture = tmpfile();
	CHECK(capture != NULL);
	capture_fd = fileno(capture);
	CHECK(capture_fd >= 0);
	saved_stdout = dup(STDOUT_FILENO);
	CHECK(saved_stdout >= 0);
	result = dup2(capture_fd, STDOUT_FILENO);
	CHECK(result == STDOUT_FILENO);
	reset(); run(0); tests++;
	CHECK(creates == 10 && releases == 10 && peak_bytes == 17969152);
	for (i = 1; i <= 10; i++) {
		reset(); fail_create = (int)i; run(1); tests++;
		CHECK(creates == (i <= 7 ? 10 : i));
		CHECK(releases == creates - 1);
	}
	for (i = 1; i <= 10; i++) {
		reset(); fail_release = (int)i; run(1); tests++;
		CHECK(creates == (i <= 7 ? i : 10));
		CHECK(releases == creates);
	}
	reset(); fail_open = true; run(1); tests++;
	CHECK(versions == 0 && creates == 0);
	reset(); fail_version = true; run(1); tests++;
	CHECK(creates == 0);
	reset(); wrong_driver = true; run(1); tests++;
	CHECK(creates == 0);
	reset(); zero_handle = true; run(1); tests++;
	CHECK(creates == 10 && releases == 9);
	reset(); fail_close = true; run(1); tests++;
	reset(); fail_create = 8; fail_errno = EINTR; run(1); tests++;
	CHECK(creates == 8 && releases == 7);
	reset(); fail_release = 8; fail_errno = EINTR; run(1); tests++;
	CHECK(creates == 10 && releases == 10);
	/* A real output failure must not skip BO or descriptor cleanup. */
	reset();
	unreadable = open("/dev/null", O_RDONLY);
	CHECK(unreadable >= 0);
	result = dup2(unreadable, STDOUT_FILENO);
	CHECK(result == STDOUT_FILENO);
	CHECK(close(unreadable) == 0);
	result = v3d_bo_alloc_main(1, args);
	CHECK(result == 1 && creates == 10 && releases == 10);
	CHECK(closed == 1 && live_bytes == 0);
	tests++;
	/* Discard the failed write buffer before restoring the real stdout. */
	CHECK(freopen("/dev/null", "w", stdout) != NULL);
	result = dup2(saved_stdout, STDOUT_FILENO);
	CHECK(result == STDOUT_FILENO);
	CHECK(close(saved_stdout) == 0);
	CHECK(fclose(capture) == 0);
	printf("PASS: %u real CLI adapter scenarios; bounded requests and cleanup\n", tests);
	return (0);
}
