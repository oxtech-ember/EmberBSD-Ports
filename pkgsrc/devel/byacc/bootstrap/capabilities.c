/* SPDX-License-Identifier: BSD-2-Clause */
/* Copyright (c) 2026 EmberBSD contributors. */
/* Origin: EmberBSD (AI-assisted). Native initial Byacc capability check. */

#include <sys/types.h>
#include <sys/stat.h>

#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdnoreturn.h>
#include <string.h>
#include <unistd.h>

static int format(char *out, size_t size, const char *fmt, ...)
    __attribute__((format(printf, 3, 4)));
static noreturn void stop(void);

static noreturn void
stop(void)
{

	exit(3);
}

static int
format(char *out, size_t size, const char *fmt, ...)
{
	va_list ap;
	int result;

	va_start(ap, fmt);
	result = vsnprintf(out, size, fmt, ap);
	va_end(ap);
	return result;
}

int
main(void)
{
	struct stat info;
	char name[] = "capability-temp.XXXXXX";
	char out[8];
	char *args[] = { "capability", "-a", NULL };
	int unused __attribute__((unused));
	int fd, result = 0;

	if (getopt(2, args, "a") != 'a' || optind != 2 ||
	    format(out, sizeof(out), "%s:%d", "v", 7) != 3 ||
	    strcmp(out, "v:7") != 0 ||
	    format(out, 3, "%s:%d", "v", 7) != 3 ||
	    strcmp(out, "v:") != 0)
		stop();
	fd = mkstemp(name);
	if (fd < 0)
		return 1;
	if (fstat(fd, &info) != 0 || !S_ISREG(info.st_mode) ||
	    (info.st_mode & 0777) != 0600 || write(fd, "x", 1) != 1)
		result = 1;
	if (close(fd) != 0 || unlink(name) != 0)
		result = 1;
	return result;
}
