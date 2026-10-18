/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Real target sysctl; no syscall substitution. */
#include <sys/types.h>
#include <sys/sysctl.h>

#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

size_t util_get_process_exec_path(char *, size_t);

static void
check(int condition, const char *message)
{

	if (!condition) {
		fprintf(stderr, "FAIL: %s\n", message);
		exit(1);
	}
}

int
main(int argc, char **argv)
{
	int mib[] = { CTL_KERN, KERN_PROC_ARGS, getpid(), KERN_PROC_PATHNAME };
	char direct[PATH_MAX], expected[PATH_MAX];
	unsigned char buffer[PATH_MAX + 2];
	char *out = (char *)buffer + 1;
	size_t size = sizeof(direct), length, got;
	int procfs = access("/proc/self/exe", F_OK) == 0;

	check(argc == 1 || (argc == 2 && strcmp(argv[1], "--require-no-proc") == 0),
	    "usage: target-probe [--require-no-proc]");
	check(argc == 1 || !procfs, "requested procfs-free execution");
	check(sysctl(mib, 4, direct, &size, NULL, 0) == 0 && size > 1 &&
	    size <= sizeof(direct) && direct[size - 1] == '\0', "real native sysctl");
	check(realpath(argv[0], expected) != NULL && strcmp(direct, expected) == 0,
	    "kernel path matches the executed probe");
	length = strlen(direct);
	check(length + 1 == size, "kernel length includes terminating NUL");
	check(util_get_process_exec_path(NULL, 0) == 0 &&
	    util_get_process_exec_path(NULL, sizeof(buffer)) == 0, "NULL inputs");
	for (size_t capacity = 0; capacity <= size; capacity++) {
		memset(buffer, 0x6d, sizeof(buffer));
		got = util_get_process_exec_path(out, capacity);
		check(buffer[0] == 0x6d && buffer[capacity + 1] == 0x6d,
		    "real syscall respects buffer bounds");
		check(got == (capacity == size ? length : 0),
		    "zero, short and exact capacities");
		if (got != 0)
			check(strcmp(out, direct) == 0, "exact buffer path");
	}
	for (unsigned i = 0; i < 4; i++) {
		got = util_get_process_exec_path(out, PATH_MAX);
		check(got == length && out[got] == '\0' && strcmp(out, direct) == 0,
		    "repeated full-buffer native query");
	}
	printf("PASS: real NetBSD sysctl path=%s length=%zu capacities=%zu procfs=%s\n",
	    direct, length, size + 1, procfs ? "present" : "absent");
	return 0;
}
