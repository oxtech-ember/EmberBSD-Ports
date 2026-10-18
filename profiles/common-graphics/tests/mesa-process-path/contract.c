/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Explicit syscall-boundary contract only. */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>

#include "sysctl-values.h"

size_t util_get_process_exec_path(char *, size_t);

static const char path[] = "/usr/pkg/bin/mesa-process-test";
static unsigned calls;
static enum { GOOD, ERROR, ZERO, OVERSIZE, NO_NUL, EMPTY } mode;

static void
check(int condition, const char *message)
{

	if (!condition) {
		fprintf(stderr, "FAIL: %s\n", message);
		exit(1);
	}
}

int
contract_sysctl(const int *mib, unsigned int count, void *out, size_t *size,
    const void *new_value, size_t new_size)
{
	size_t capacity = *size;

	calls++;
	check(count == 4 && mib[0] == CTL_KERN && mib[1] == KERN_PROC_ARGS &&
	    mib[2] == getpid() && mib[3] == KERN_PROC_PATHNAME,
	    "native NetBSD process-path MIB");
	check(out != NULL && capacity != 0 && new_value == NULL && new_size == 0,
	    "read-only bounded sysctl");
	if (mode == ERROR) {
		errno = EIO;
		return -1;
	}
	if (mode == ZERO || mode == OVERSIZE) {
		*size = mode == ZERO ? 0 : capacity + 1;
		return 0;
	}
	if (mode == EMPTY) {
		*(char *)out = '\0';
		*size = 1;
		return 0;
	}
	memcpy(out, path, capacity < sizeof(path) ? capacity : sizeof(path));
	*size = sizeof(path);
	if (capacity < sizeof(path)) {
		errno = ENOSPC;
		return -1;
	}
	if (mode == NO_NUL)
		((char *)out)[sizeof(path) - 1] = 'X';
	return 0;
}

ssize_t
contract_readlink(const char *name, char *out, size_t size)
{

	(void)name;
	(void)out;
	(void)size;
	errno = ENOENT;
	return -1;
}

int
main(void)
{
	unsigned char buffer[128];
	char *out = (char *)buffer + 1;
	size_t got;

	memset(buffer, 0x6d, sizeof(buffer));
	got = util_get_process_exec_path(out, sizeof(buffer) - 2);
	check(got == sizeof(path) - 1 && strcmp(out, path) == 0 && calls == 1,
	    "path works without procfs and excludes its terminating NUL");
	for (size_t capacity = 0; capacity <= sizeof(path); capacity++) {
		memset(buffer, 0x6d, sizeof(buffer));
		calls = 0;
		got = util_get_process_exec_path(out, capacity);
		check(buffer[0] == 0x6d && buffer[capacity + 1] == 0x6d,
		    "caller buffer bounds");
		check(got == (capacity == sizeof(path) ? sizeof(path) - 1 : 0),
		    "zero, short and exact buffer capacities");
		check(calls == (capacity == 0 ? 0U : 1U), "zero capacity avoids sysctl");
	}
	calls = 0;
	check(util_get_process_exec_path(NULL, 0) == 0 &&
	    util_get_process_exec_path(NULL, 128) == 0 && calls == 0,
	    "NULL avoids sysctl");
	for (mode = ERROR; mode <= EMPTY; mode++) {
		memset(buffer, 0, sizeof(buffer));
		buffer[65] = 0x6d;
		calls = 0;
		check(util_get_process_exec_path(out, 64) == 0 && calls == 1 &&
		    buffer[65] == 0x6d, "failed or malformed sysctl output is rejected");
	}
	puts("PASS: native MIB, absent procfs, NULL/zero/short/exact buffers, syscall errors and NUL bounds");
	return 0;
}
