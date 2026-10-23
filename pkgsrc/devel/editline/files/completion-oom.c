/* Verify allocation-failure ownership in the real libedit completion code.
 * Link the static library with --wrap=realloc,calloc,free.
 * Prepared with AI assistance.
 */
#include <sys/types.h>
#include <editline/readline.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void *strings[16];
static size_t live;
static int active, fail_realloc, fail_calloc, realloc_calls, calloc_calls;

void *__real_realloc(void *, size_t);
void *__real_calloc(size_t, size_t);
void __real_free(void *);

void *
__wrap_realloc(void *ptr, size_t size)
{
	if (active && ++realloc_calls == fail_realloc) {
		errno = ENOMEM;
		return NULL;
	}
	return __real_realloc(ptr, size);
}

void *
__wrap_calloc(size_t number, size_t size)
{
	if (active && ++calloc_calls == fail_calloc) {
		errno = ENOMEM;
		return NULL;
	}
	return __real_calloc(number, size);
}

void
__wrap_free(void *ptr)
{
	size_t i;

	if (ptr != NULL) {
		for (i = 0; i < sizeof(strings) / sizeof(strings[0]); i++) {
			if (strings[i] == ptr) {
				strings[i] = NULL;
				live--;
				break;
			}
		}
	}
	__real_free(ptr);
}

static char *
generate(const char *text, int state)
{
	char *str;

	(void)text;
	if (state == 12)
		return NULL;
	if (state < 0 || state >= 12)
		abort();
	str = malloc(32);
	if (str == NULL)
		abort();
	(void)snprintf(str, 32, "candidate-%02d", state);
	strings[state] = str;
	live++;
	return str;
}

int
main(int argc, char **argv)
{
	char **matches;
	int test, i;

	if (argc > 2 || (argc == 2 && strcmp(argv[1], "readline") != 0))
		return EXIT_FAILURE;
	for (test = argc == 2 ? 5 : 0; test < 5; test++) {
		fail_realloc = test >= 1 && test <= 3 ? test : 0;
		fail_calloc = test == 4 ? 1 : 0;
		realloc_calls = calloc_calls = 0;
		active = 1;
		matches = completion_matches("candidate", generate);
		active = 0;
		if (test == 0) {
			if (matches == NULL || strcmp(matches[0], "candidate-") != 0)
				return EXIT_FAILURE;
			for (i = 0; matches[i] != NULL; i++)
				free(matches[i]);
			free(matches);
			if (i != 13)
				return EXIT_FAILURE;
		} else if (matches != NULL ||
		    (fail_realloc && realloc_calls != fail_realloc) ||
		    (fail_calloc && calloc_calls != fail_calloc)) {
			fprintf(stderr, "failure injection did not trigger: %d\n", test);
			return EXIT_FAILURE;
		}
		if (live != 0) {
			fprintf(stderr, "case %d leaked %zu generated strings\n", test, live);
			return EXIT_FAILURE;
		}
	}
	fail_realloc = 1;
	fail_calloc = 0;
	realloc_calls = calloc_calls = 0;
	active = 1;
	matches = rl_completion_matches("candidate", generate);
	active = 0;
	if (matches != NULL || realloc_calls != 1 || live != 0) {
		fprintf(stderr, "readline growth failure leaked %zu strings\n", live);
		return EXIT_FAILURE;
	}
	puts("PASS: completion ownership on injected allocation failures");
	return EXIT_SUCCESS;
}
