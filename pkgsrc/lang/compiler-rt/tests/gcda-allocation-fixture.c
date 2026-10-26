/* SPDX-License-Identifier: BSD-2-Clause */
/* Copyright (c) 2026 The EmberBSD Project contributors. */
/* Developed with AI assistance. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static int fail_malloc, fail_realloc, fail_strdup, stream_fd = -1;
static unsigned callbacks;

void *
fixture_malloc(size_t size)
{

	if (fail_malloc) { errno = ENOMEM; return NULL; }
	return malloc(size);
}

void *
fixture_realloc(void *pointer, size_t size)
{

	if (fail_realloc) { errno = ENOMEM; return NULL; }
	return realloc(pointer, size);
}

char *
fixture_strdup(const char *text)
{

	if (fail_strdup) { errno = ENOMEM; return NULL; }
	return strdup(text);
}

FILE *
fixture_fdopen(int fd, const char *mode)
{

	stream_fd = fd;
	return fdopen(fd, mode);
}

void llvm_register_writeout_function(void (*)(void));
void llvm_delete_writeout_function_list(void);
void llvm_writeout_files(void);
void llvm_gcda_emit_arcs(uint32_t, uint64_t *);
void llvm_gcda_summary_info(void);
void llvm_gcda_end_file(void);
#ifdef TEST_CURRENT_GCOV_ABI
void llvm_gcda_start_file(const char *, uint32_t, uint32_t);
#else
void llvm_gcda_start_file(const char *, const char[4], uint32_t);
#endif

static void
callback(void)
{

	callbacks++;
}

static void
start(const char *name)
{

#ifdef TEST_CURRENT_GCOV_ABI
	llvm_gcda_start_file(name, UINT32_C(0x3430382a), 1);
#else
	llvm_gcda_start_file(name, "*804", 1);
#endif
}

static void
closed(void)
{
	int result;

	assert(stream_fd >= 0);
	errno = 0;
	result = fcntl(stream_fd, F_GETFD);
	assert(result == -1 && errno == EBADF);
}

int
main(int argc, char **argv)
{
	uint64_t counter = 3;
	struct stat status;
	int result;

	assert(argc == 3);
	if (strcmp(argv[2], "callback") == 0) {
		fail_malloc = 1;
		llvm_register_writeout_function(callback);
		fail_malloc = 0;
		llvm_register_writeout_function(callback);
		llvm_writeout_files();
		assert(callbacks == 1);
#ifndef TEST_CURRENT_GCOV_ABI
		llvm_delete_writeout_function_list();
		llvm_writeout_files();
		assert(callbacks == 1);
#else
		llvm_writeout_files();
		assert(callbacks == 2);
#endif
	} else if (strcmp(argv[2], "filename") == 0 ||
	    strcmp(argv[2], "prefixed-filename") == 0) {
		if (strcmp(argv[2], "prefixed-filename") == 0) {
			result = setenv("GCOV_PREFIX", argv[1], 1);
			assert(result == 0);
			fail_malloc = 1;
		} else {
			fail_strdup = 1;
		}
		start(argv[1]);
		llvm_gcda_emit_arcs(1, &counter);
		llvm_gcda_summary_info();
		llvm_gcda_end_file();
		assert(stream_fd == -1 && counter == 3);
		result = stat(argv[1], &status);
		assert(result == -1 && errno == ENOENT);
	} else if (strcmp(argv[2], "counter-size-overflow") == 0) {
		start(argv[1]);
		llvm_gcda_emit_arcs(UINT32_C(0x20000000), &counter);
		llvm_gcda_end_file();
		closed();
		result = stat(argv[1], &status);
		assert(result == 0 && status.st_size == 0 && counter == 3);
	} else if (strcmp(argv[2], "merge") == 0) {
		unsigned char before[256], after[256];
		size_t length, after_length;
		FILE *file;

		start(argv[1]);
		llvm_gcda_emit_arcs(1, &counter);
		llvm_gcda_end_file();
		closed();
		file = fopen(argv[1], "rb");
		assert(file != NULL);
		length = fread(before, 1, sizeof(before), file);
		result = fclose(file);
		assert(result == 0 && length > 0 && length < sizeof(before));
		start(argv[1]);
		fail_malloc = 1;
		llvm_gcda_emit_arcs(1, &counter);
		llvm_gcda_summary_info();
		llvm_gcda_end_file();
		closed();
		assert(counter == 3);
		file = fopen(argv[1], "rb");
		assert(file != NULL);
		after_length = fread(after, 1, sizeof(after), file);
		result = fclose(file);
		assert(result == 0 && after_length == length);
		assert(memcmp(before, after, length) == 0);
	} else {
		if (strcmp(argv[2], "initial-buffer") == 0) {
			fail_realloc = 1;
			start(argv[1]);
			llvm_gcda_emit_arcs(1, &counter);
		} else {
			uint64_t *counters;

			assert(strcmp(argv[2], "growing-buffer") == 0);
			counters = calloc(17000, sizeof(*counters));
			assert(counters != NULL);
			start(argv[1]);
			fail_realloc = 1;
			llvm_gcda_emit_arcs(17000, counters);
			free(counters);
		}
		llvm_gcda_summary_info();
		llvm_gcda_end_file();
		closed();
		result = stat(argv[1], &status);
		assert(result == 0 && status.st_size == 0);
	}
	puts("PASS: allocation failure preserves state and releases resources");
	return 0;
}
