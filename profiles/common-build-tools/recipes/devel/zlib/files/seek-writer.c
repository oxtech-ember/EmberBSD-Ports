/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted); gzip writer seek regression. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>

static void
require(int pass, const char *message)
{

	if (!pass) {
		fprintf(stderr, "FAIL: %s\n", message);
		exit(EXIT_FAILURE);
	}
}

int
main(int argc, char **argv)
{
	gzFile file;
	unsigned char bytes[6];
	int mode;
	const char *modes[] = { "wb", "ab" };

	require(argc == 2, "pass a private output path");
	require(strcmp(zlibVersion(), ZLIB_VERSION) == 0, "header/runtime version");
	for (mode = 0; mode != 2; mode++) {
		file = gzopen(argv[1], modes[mode]);
		require(file != NULL, "open compressed writer");
		require(gztell(file) == 0, "initial writer position");
		require(gzseek(file, 3, SEEK_CUR) == 3, "first deferred writer seek");
		require(gzseek(file, 2, SEEK_CUR) == 5, "accumulate deferred writer seek");
		require(gztell(file) == 5, "deferred writer position");
		require(gzputc(file, 'X') == 'X', "write after seek");
		require(gztell(file) == 6, "written position");
		require(gzseek(file, -1, SEEK_CUR) == -1, "reject backward writer seek");
		require(gzclose(file) == Z_OK, "close compressed writer");
	}
	file = gzopen(argv[1], "rb");
	require(file != NULL, "open concatenated gzip members");
	for (mode = 0; mode != 2; mode++) {
		memset(bytes, 0xff, sizeof(bytes));
		require(gzread(file, bytes, sizeof(bytes)) == sizeof(bytes), "read member");
		require(memcmp(bytes, "\0\0\0\0\0X", sizeof(bytes)) == 0,
		    "seek zero fill and payload");
	}
	require(gzread(file, bytes, 1) == 0 && gzeof(file), "gzip end of file");
	require(gzclose(file) == Z_OK, "close compressed reader");
	require(gzseek(NULL, 0, SEEK_CUR) == -1 && gztell(NULL) == -1,
	    "null handle rejection");
	puts("PASS: gzip writer, append, deferred seek and concatenated members");
	return EXIT_SUCCESS;
}
