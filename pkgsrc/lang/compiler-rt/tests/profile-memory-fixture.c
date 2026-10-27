/* SPDX-License-Identifier: BSD-2-Clause */
/* Copyright (c) 2026 The EmberBSD Project contributors. */
/* Developed with AI assistance. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "InstrProfiling.h"
#include "InstrProfilingInternal.h"

void __llvm_profile_set_filename(const char *);
int __llvm_profile_runtime = 0;
static int fail_writer, fail_buffer;
static void *allocations[16];
static unsigned nallocations, live, released, foreign_frees;

static void *
remember(void *p)
{
	assert(p != NULL && nallocations < 16);
	allocations[nallocations++] = p;
	live++;
	return p;
}

void *
fixture_calloc(size_t n, size_t size)
{
	if ((fail_writer && n == 1 && size == sizeof(ProfDataWriter)) ||
	    (fail_buffer && n == 1 && size == 64)) {
		errno = ENOMEM;
		return NULL;
	}
	return remember(calloc(n, size));
}

char *
fixture_strdup(const char *s)
{
	return remember(strdup(s));
}

void
fixture_free(void *p)
{
	for (unsigned i = 0; i < nallocations; i++) {
		if (p != NULL && allocations[i] == p) {
			allocations[i] = NULL;
			live--;
			released++;
			break;
		}
	}
	free(p);
}

static void
foreign_free(void *p)
{
	(void)p;
	foreign_frees++;
	abort();
}

static void
roundtrip(void)
{
	static const uint8_t bytes[] = "buffered profile data\n";
	uint8_t actual[sizeof(bytes)];
	FILE *file = tmpfile();
	ProfBufferIO *io;

	assert(file != NULL);
	io = lprofCreateBufferIOInternal(file, 64);
	assert(io != NULL && io->OwnFileWriter == 1);
	assert(io->BufferSz == (fail_buffer ? 8192 : 64));
	assert(live == (fail_buffer ? 1U : 2U));
	assert(lprofBufferIOWrite(io, bytes, sizeof(bytes)) == 0);
	assert(lprofBufferIOFlush(io) == 0);
	rewind(file);
	assert(fread(actual, 1, sizeof(actual), file) == sizeof(actual));
	assert(memcmp(actual, bytes, sizeof(bytes)) == 0);
	lprofDeleteBufferIO(io);
	assert(live == 0 && DynamicBufferIOBuffer == NULL);
	assert(fclose(file) == 0);
}

int
main(int argc, char **argv)
{
	const char *mode, *name, *expected = "new.profraw";
	int result;

	assert(argc == 2);
	mode = argv[1];
	unsetenv("LLVM_PROFILE_VERBOSE");
	unsetenv("LLVM_PROFILE_FILE");
	if (strncmp(mode, "io-", 3) == 0) {
		if (strcmp(mode, "io-writer-failure") == 0 ||
		    strcmp(mode, "io-foreign-buffer") == 0) {
			uint8_t *saved = NULL;
			if (strcmp(mode, "io-foreign-buffer") == 0) {
				saved = remember(malloc(13));
				saved[0] = 42;
			}
			DynamicBufferIOBuffer = saved;
			VPBufferSize = 13;
			FreeHook = foreign_free;
			fail_writer = 1;
			assert(lprofCreateBufferIOInternal(NULL, 64) == NULL);
			assert(DynamicBufferIOBuffer == saved && VPBufferSize == 13);
			assert(FreeHook == foreign_free && foreign_frees == 0);
			assert(live == (saved ? 1U : 0U));
			if (saved) assert(saved[0] == 42);
			fixture_free(saved);
			DynamicBufferIOBuffer = NULL;
			assert(live == 0);
		} else {
			fail_buffer = strcmp(mode, "io-buffer-failure") == 0;
			for (int i = 0; i < 3; i++) roundtrip();
			assert(released == (fail_buffer ? 3U : 6U));
		}
		puts("IO ownership and data PASS");
		return 0;
	}
	if (strcmp(mode, "quiet") != 0)
		assert(setenv("LLVM_PROFILE_VERBOSE", "1", 1) == 0);
	if (strcmp(mode, "environment") == 0) {
		assert(setenv("LLVM_PROFILE_FILE", "environment.profraw", 1) == 0);
		__llvm_profile_initialize_file();
	} else if (strcmp(mode, "borrowed") == 0) {
		__llvm_profile_initialize_file();
	} else {
		__llvm_profile_set_filename("old.profraw");
	}
	if (strcmp(mode, "same") == 0) expected = "old.profraw";
	if (strcmp(mode, "default") == 0 || strcmp(mode, "invalid") == 0)
		expected = "default.profraw";
	if (strcmp(mode, "invalid") == 0) {
		unsetenv("TMPDIR");
		__llvm_profile_set_filename("%t/no-temp.profraw");
	} else {
		__llvm_profile_set_filename(strcmp(mode, "default") == 0 ? NULL : expected);
	}
	name = __llvm_profile_get_filename();
	result = strcmp(name, expected);
	free((void *)name);
	assert(result == 0);
	assert(live == (strcmp(mode, "invalid") == 0 ? 0U : 1U));
	assert(released == (strcmp(mode, "invalid") == 0 ? 2U :
	    strcmp(mode, "same") == 0 || strcmp(mode, "borrowed") == 0 ? 0U : 1U));
	puts("filename ownership and result PASS");
	return 0;
}
