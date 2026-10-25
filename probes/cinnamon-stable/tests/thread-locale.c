/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). POSIX thread-locale acceptance probe. */

#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <langinfo.h>
#include <locale.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef __APPLE__
#include <xlocale.h>
#endif

/* A deliberate fault must fail the same public-interface checks. */
#ifdef EMBERBSD_TEST_NOOP_USELOCALE
static locale_t
noop_uselocale(locale_t requested)
{

	(void)requested;
	return LC_GLOBAL_LOCALE;
}
#define uselocale noop_uselocale
#endif

static void
require(int condition, const char *operation)
{

	if (!condition) {
		fprintf(stderr, "FAIL: %s (errno=%d)\n", operation, errno);
		exit(EXIT_FAILURE);
	}
}

struct worker_state {
	pthread_mutex_t mutex;
	pthread_cond_t condition;
	locale_t locale;
	int ready;
	int release;
};

static void *
worker(void *argument)
{
	struct worker_state *state = argument;
	locale_t previous;

	require(uselocale((locale_t)0) == LC_GLOBAL_LOCALE,
	    "new thread starts with the global locale");
	previous = uselocale(state->locale);
	require(previous == LC_GLOBAL_LOCALE, "worker receives previous locale");
	require(uselocale((locale_t)0) == state->locale,
	    "worker query returns its selected locale");
	require(strcmp(localeconv()->decimal_point, ".") == 0,
	    "worker uses its own C numeric locale");
	require(pthread_mutex_lock(&state->mutex) == 0, "worker locks state");
	state->ready = 1;
	require(pthread_cond_signal(&state->condition) == 0, "worker signals ready");
	while (!state->release)
		require(pthread_cond_wait(&state->condition, &state->mutex) == 0,
		    "worker waits for release");
	require(pthread_mutex_unlock(&state->mutex) == 0, "worker unlocks state");
	require(uselocale(previous) == state->locale, "worker restores previous locale");
	return NULL;
}

int
main(int argc, char **argv)
{
	struct worker_state state = {
		.mutex = PTHREAD_MUTEX_INITIALIZER,
		.condition = PTHREAD_COND_INITIALIZER,
	};
	const char *numeric_name = argc > 1 ? argv[1] : "de_DE.UTF-8";
	locale_t numeric, duplicate, previous;
	pthread_t thread;
	char *end;

	require(setlocale(LC_ALL, "C") != NULL, "select global C locale");
	require(uselocale((locale_t)0) == LC_GLOBAL_LOCALE, "query global selector");
	state.locale = newlocale(LC_ALL_MASK, "C", (locale_t)0);
	require(state.locale != (locale_t)0, "create C locale");
	numeric = newlocale(LC_NUMERIC_MASK, numeric_name, (locale_t)0);
	if (numeric == (locale_t)0) {
		fprintf(stderr, "Required test locale is unavailable: %s\n", numeric_name);
		freelocale(state.locale);
		return 77;
	}
	require(strcmp(nl_langinfo_l(RADIXCHAR, numeric), ",") == 0,
	    "independent numeric locale has comma radix");
	previous = uselocale(numeric);
	require(previous == LC_GLOBAL_LOCALE, "selection returns previous global locale");
	require(uselocale((locale_t)0) == numeric, "query does not change selection");
	require(strcmp(localeconv()->decimal_point, ",") == 0,
	    "localeconv follows the thread selector");
	require(strcmp(nl_langinfo(RADIXCHAR), ",") == 0,
	    "nl_langinfo follows the thread selector");
	require(strtod("1,5", &end) == 1.5 && *end == '\0',
	    "strtod follows the thread selector");
	require(strcmp(setlocale(LC_NUMERIC, NULL), "C") == 0,
	    "setlocale queries the global numeric locale");
	duplicate = duplocale(uselocale((locale_t)0));
	require(duplicate != (locale_t)0, "duplicate selected locale");
	require(uselocale(duplicate) == numeric, "select duplicate and retain previous handle");
	require(uselocale(numeric) == duplicate, "restore original selected handle");
	freelocale(duplicate);

	require(pthread_create(&thread, NULL, worker, &state) == 0, "create worker");
	require(pthread_mutex_lock(&state.mutex) == 0, "main locks state");
	while (!state.ready)
		require(pthread_cond_wait(&state.condition, &state.mutex) == 0,
		    "main waits for worker selection");
	require(uselocale((locale_t)0) == numeric, "worker does not replace main selector");
	require(strcmp(localeconv()->decimal_point, ",") == 0,
	    "worker does not replace main numeric locale");
	state.release = 1;
	require(pthread_cond_signal(&state.condition) == 0, "main releases worker");
	require(pthread_mutex_unlock(&state.mutex) == 0, "main unlocks state");
	require(pthread_join(thread, NULL) == 0, "join worker");
	require(pthread_cond_destroy(&state.condition) == 0, "destroy condition");
	require(pthread_mutex_destroy(&state.mutex) == 0, "destroy mutex");
	require(uselocale(previous) == numeric, "restore global selector");
	require(strcmp(localeconv()->decimal_point, ".") == 0,
	    "global selection restores numeric behavior");
	freelocale(numeric);
	freelocale(state.locale);
	puts("PASS: selection, query, libc dispatch, duplication and thread isolation");
	return EXIT_SUCCESS;
}
