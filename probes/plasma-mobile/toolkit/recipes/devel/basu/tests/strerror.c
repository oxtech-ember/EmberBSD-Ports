/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Test the included upstream functions. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "sd-bus.h"
#include "alloc-util.h"

#ifdef __GLIBC__
#error This regression needs the POSIX strerror_r branch on a BSD host.
#endif

/* Preserve fatal assertions without linking the unrelated logging backend. */
_noreturn_ void
log_assert_failed_realm(LogRealm realm, const char *text, const char *file,
    int line, const char *function)
{
	(void)realm;
	fprintf(stderr, "%s:%d: %s: assertion failed: %s\n", file, line,
	    function, text);
	abort();
}

static const char *test_mode;
static unsigned int call_count;
static size_t seen_size[2];

static int
injected_strerror_r(int error, char *buffer, size_t length)
{
	unsigned int call = call_count++;

	assert(call < 2);
	seen_size[call] = length;
	if (strcmp(test_mode, "error") == 0)
		return EINVAL;
	if (strcmp(test_mode, "range") == 0 && call == 0)
		return ERANGE;
	if (strcmp(test_mode, "full") == 0 && call == 0) {
		memset(buffer, 'x', length - 1);
		buffer[length - 1] = '\0';
		return 0;
	}
	if (strcmp(test_mode, "native") == 0)
		return strerror_r(error, buffer, length);
	assert(length > strlen("fixture message"));
	strcpy(buffer, "fixture message");
	return 0;
}

/* Only the external conversion call is injected. Both function bodies and
 * the allocation helpers come from the selected source tree. */
#define strerror_r injected_strerror_r
#include "strerror-functions.inc"
#undef strerror_r

int
main(int argc, char **argv)
{
	sd_bus_error error = { "org.example.TestError", "original message", 0 };
	const char *original_name, *original_message;
	bool dynamic;

	assert(argc == 3);
	test_mode = argv[1];
	dynamic = strcmp(argv[2], "dynamic") == 0;
	assert(dynamic || strcmp(argv[2], "constant") == 0);
	if (dynamic) {
		error.name = strdup(error.name);
		error.message = strdup(error.message);
		assert(error.name != NULL && error.message != NULL);
		error._need_free = 1;
	}
	original_name = error.name;
	original_message = error.message;
	bus_error_strerror(&error, EINVAL);
	assert(seen_size[0] == 64);
	if (strcmp(test_mode, "error") == 0) {
		assert(call_count == 1);
		assert(errno == EINVAL);
		assert(error.name == original_name);
		assert(error.message == original_message);
		assert(error._need_free == (dynamic ? 1 : 0));
	} else {
		assert(strcmp(error.name, "org.example.TestError") == 0);
		assert(error._need_free == 1);
		if (dynamic)
			assert(error.name == original_name);
		if (strcmp(test_mode, "range") == 0 || strcmp(test_mode, "full") == 0) {
			assert(call_count == 2);
			assert(seen_size[1] == 128);
		} else
			assert(call_count == 1);
		if (strcmp(test_mode, "native") == 0)
			assert(error.message != NULL && error.message[0] != '\0');
		else
			assert(strcmp(error.message, "fixture message") == 0);
	}
	if (error._need_free > 0) {
		free((char *)error.name);
		free((char *)error.message);
	}
	puts("PASS: actual basu strerror functions and error ownership");
	return 0;
}
