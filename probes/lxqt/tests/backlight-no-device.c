/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Check the real helper's no-device path. */
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int checked_snprintf(char *, size_t, const char *, ...);
static char *tracked_strdup(const char *);
static void tracked_free(void *);
static FILE *tracked_fopen(const char *, const char *);
static int allocations, releases, writes;

/* Enforce the %s contract without relying on libc's handling of NULL. */
#define snprintf checked_snprintf
#define strdup tracked_strdup
#define free tracked_free
#define fopen tracked_fopen
#define main upstream_main
#include "lxqtbacklight_backend.c"
#undef main
#undef snprintf
#undef strdup
#undef free
#undef fopen

static char *
tracked_strdup(const char *text)
{
	char *copy;

	copy = strdup(text);
	if (copy != NULL)
		allocations++;
	return copy;
}

static void
tracked_free(void *pointer)
{

	if (pointer != NULL)
		releases++;
	free(pointer);
}

static FILE *
tracked_fopen(const char *path, const char *mode)
{
	FILE *stream;

	stream = fopen(path, mode);
	if (stream != NULL && strcmp(mode, "w") == 0)
		writes++;
	return stream;
}

static int
checked_snprintf(char *buffer, size_t size, const char *format, ...)
{
	va_list arguments, probe;
	const char *driver;
	int result;

	if (strcmp(format, "%s/%s/%s") != 0)
		exit(2);
	va_start(arguments, format);
	va_copy(probe, arguments);
	(void)va_arg(probe, const char *);
	driver = va_arg(probe, const char *);
	va_end(probe);
	if (driver == NULL) {
		fputs("FAIL: the helper formatted a null driver\n", stderr);
		exit(42);
	}
	result = vsnprintf(buffer, size, format, arguments);
	va_end(arguments);
	return result;
}

int
main(int argc, char **argv)
{

	if (argc < 2 || argc > 3)
		return 2;
	/* Use a private empty or synthetic device directory. Never use hardware. */
	sysfs_backlight_dir = argv[1];
	if (argc == 3) {
		if (read_max_backlight(argv[2]) != -1)
			return 44;
	} else {
		set_backlight_from_stdin();
	}
	if (allocations != releases) {
		fputs("FAIL: a backlight driver allocation remains owned\n", stderr);
		return 43;
	}
	printf("writes=%d\n", writes);
	return 0;
}
