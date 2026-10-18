/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Compile the actual upstream module. */
#ifndef NGSPICE_HISTORY_SOURCE
#error "Set NGSPICE_HISTORY_SOURCE to the absolute com_history.c path"
#endif
#include NGSPICE_HISTORY_SOURCE

FILE *cp_err;

/* Supply only allocation and string primitives for the isolated function. */
void *
tmalloc(size_t size)
{
	void *p = calloc(1, size);
	if (!p)
		exit(2);
	return p;
}

void
txfree(const void *p)
{
	free((void *)p);
}

char *
dup_string(const char *text, size_t size)
{
	char *result = tmalloc(size + 1);
	memcpy(result, text, size);
	return result;
}

int
prefix(const char *pattern, const char *text)
{
	return strncmp(pattern, text, strlen(pattern)) == 0;
}

static void
require(bool good)
{
	if (!good) {
		fputs("FAIL: history substitution\n", stderr);
		exit(1);
	}
}

int
main(void)
{
	const size_t length = 32768;
	char *pattern = tmalloc(length + 5);
	char *result;

	cp_err = stderr;
	pattern[0] = '/';
	pattern[1] = 'x';
	pattern[2] = '/';
	memset(pattern + 3, 'a', length);
	pattern[length + 3] = '/';
	pattern[length + 4] = '\0';
	for (int i = 0; i < 16; ++i) {
		result = dohs(pattern, "x-tail-x");
		require(result && strlen(result) == length + 7);
		for (size_t j = 0; j < length; ++j)
			require(result[j] == 'a');
		require(strcmp(result + length, "-tail-x") == 0);
		txfree(result);
	}
	free(pattern);
	result = dohs("/x//", "before-x-end");
	require(result && strcmp(result, "before--end") == 0);
	txfree(result);
	require(dohs("/absent/word/", "original") == NULL);
	require(dohs("/broken", "original") == NULL);
	require(dohs("//replacement/", "original") == NULL);
	require(dohs(NULL, "original") == NULL);
	require(dohs("/x/y/", NULL) == NULL);
	puts("PASS: long, first-match, empty, absent and malformed history substitution");
	return 0;
}
