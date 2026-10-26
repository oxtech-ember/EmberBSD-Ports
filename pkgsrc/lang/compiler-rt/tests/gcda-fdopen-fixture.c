/* SPDX-License-Identifier: BSD-2-Clause */
/* Copyright (c) 2026 The EmberBSD Project contributors. */
/* Developed with AI assistance. */
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>

static int stream_fd = -1;
FILE *
fixture_fdopen(int fd, const char *mode)
{
	(void)mode;
	stream_fd = fd;
	errno = ENOMEM;
	return NULL;
}
#ifdef TEST_CURRENT_GCOV_ABI
void llvm_gcda_start_file(const char *, uint32_t, uint32_t);
#else
void llvm_gcda_start_file(const char *, const char[4], uint32_t);
#endif
void llvm_gcda_end_file(void);

int
main(int argc, char **argv)
{
	int result;

	assert(argc == 2);
#ifdef TEST_CURRENT_GCOV_ABI
	llvm_gcda_start_file(argv[1], UINT32_C(0x3430382a), 1);
#else
	llvm_gcda_start_file(argv[1], "*804", 1);
#endif
	assert(stream_fd >= 0);
	errno = 0;
	result = fcntl(stream_fd, F_GETFD);
	assert(result == -1 && errno == EBADF);
	llvm_gcda_end_file();
	puts("PASS: failed fdopen releases its descriptor and permits cleanup");
	return 0;
}
