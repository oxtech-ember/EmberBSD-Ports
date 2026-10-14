/*
 * SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD, AI-assisted.
 * Include the real allocator to exercise its private metadata constructors.
 * Link the real ggml.c fatal handler. Replace only malloc/calloc in this file.
 */

#include <sys/types.h>
#include <sys/resource.h>
#include <sys/wait.h>

#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "ggml-impl.h"

enum failure_kind {
	FAIL_NONE,
	FAIL_MALLOC,
	FAIL_CALLOC
};

static enum failure_kind failure;
static unsigned int injected;
static int abort_pipe;
static const char *expected_assert;

static void *
fixture_malloc(size_t size)
{
	if (failure == FAIL_MALLOC) {
		failure = FAIL_NONE;
		injected++;
		errno = ENOMEM;
		return (NULL);
	}
	return (malloc(size));
}

static void *
fixture_calloc(size_t count, size_t size)
{
	if (failure == FAIL_CALLOC) {
		failure = FAIL_NONE;
		injected++;
		errno = ENOMEM;
		return (NULL);
	}
	return (calloc(count, size));
}

#define malloc fixture_malloc
#define calloc fixture_calloc
#include "ggml-alloc.c"
#undef malloc
#undef calloc

static void
require(int condition, const char *message)
{
	if (!condition) {
		fprintf(stderr, "%s\n", message);
		exit(EXIT_FAILURE);
	}
}

static void
observe_abort(const char *message)
{
	const char mark = 'A';

	if (injected != 1 || strstr(message, expected_assert) == NULL ||
	    write(abort_pipe, &mark, sizeof(mark)) != sizeof(mark))
		_exit(3);
	/* Return to the real ggml_abort, which must terminate with SIGABRT. */
}

static int
check_failure(enum failure_kind kind, const char *assertion)
{
	struct ggml_dyn_tallocr *alloc;
	pid_t child, waited;
	int pipes[2], status;
	char mark = 0;
	ssize_t count;

	require(pipe(pipes) == 0, "pipe failed");
	child = fork();
	require(child >= 0, "fork failed");
	if (child == 0) {
		(void)close(pipes[0]);
		abort_pipe = pipes[1];
		expected_assert = assertion;
		(void)ggml_set_abort_callback(observe_abort);
		if (kind == FAIL_MALLOC) {
			failure = kind;
			alloc = ggml_dyn_tallocr_new(32, 1024);
		} else {
			alloc = ggml_dyn_tallocr_new(32, 1024);
			failure = kind;
			(void)ggml_dyn_tallocr_new_chunk(alloc, 64);
		}
		/* A constructor must not return after its metadata allocation fails. */
		ggml_dyn_tallocr_free(alloc);
		_exit(4);
	}
	(void)close(pipes[1]);
	do {
		waited = waitpid(child, &status, 0);
	} while (waited == -1 && errno == EINTR);
	require(waited == child, "waitpid failed");
	do {
		count = read(pipes[0], &mark, sizeof(mark));
	} while (count == -1 && errno == EINTR);
	(void)close(pipes[0]);
	if (!WIFSIGNALED(status) || WTERMSIG(status) != SIGABRT ||
	    count != sizeof(mark) || mark != 'A') {
		fprintf(stderr, "%s: expected GGML_ASSERT and SIGABRT; status=%d, diagnostic=%d\n",
		    kind == FAIL_MALLOC ? "malloc" : "calloc", status,
		    count == sizeof(mark) && mark == 'A');
		return (1);
	}
	printf("PASS: %s failure reaches GGML_ASSERT and SIGABRT\n",
	    kind == FAIL_MALLOC ? "malloc" : "calloc");
	return (0);
}

int
main(int argc, char **argv)
{
	struct ggml_dyn_tallocr *alloc;
	struct rlimit cores = { 0, 0 };
	int failures = 0;

	require(argc == 1 || (argc == 2 &&
	    strcmp(argv[1], "--success-only") == 0), "invalid arguments");
	require(setrlimit(RLIMIT_CORE, &cores) == 0, "setrlimit failed");
	alloc = ggml_dyn_tallocr_new(32, 1024);
	require(alloc->alignment == 32 && alloc->max_chunk_size == 1024 &&
	    alloc->n_chunks == 0, "new allocator state is invalid");
	require(ggml_dyn_tallocr_new_chunk(alloc, 64) == 0 &&
	    alloc->n_chunks == 1 && alloc->chunks[0]->n_free_blocks == 1 &&
	    alloc->chunks[0]->free_blocks[0].offset == 0 &&
	    alloc->chunks[0]->free_blocks[0].size == 1024,
	    "new chunk state is invalid");
	ggml_dyn_tallocr_reset(alloc);
	require(alloc->n_chunks == 0 && alloc->chunks[0] == NULL,
	    "reset did not release its chunk");
	ggml_dyn_tallocr_free(alloc);
	puts("PASS: successful metadata allocation, reset, and free");
	if (argc == 1) {
		(void)fflush(stdout);
		failures += check_failure(FAIL_MALLOC,
		    "GGML_ASSERT(alloc != NULL) failed");
		(void)fflush(stdout);
		failures += check_failure(FAIL_CALLOC,
		    "GGML_ASSERT(chunk != NULL) failed");
	}
	return (failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE);
}
