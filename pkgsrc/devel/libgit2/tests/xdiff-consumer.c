/* SPDX-License-Identifier: BSD-2-Clause */
/* Developed with AI assistance. */
#include <git2.h>
#include <git2/sys/alloc.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static size_t allocations;
static size_t releases;
static size_t zero_allocations;
static int fail_xdiff_allocation;
static int xdiff_failure_hit;
static int lines;

static void *
counted_malloc(size_t size, const char *file, int line)
{
	(void)file;
	(void)line;
	allocations++;
	if (fail_xdiff_allocation && allocations == 3 &&
	    size == 16 * sizeof(void *)) {
		xdiff_failure_hit = 1;
		return NULL;
	}
	if (size == 0) {
		zero_allocations++;
		return NULL;
	}
	return malloc(size);
}

static void *
counted_realloc(void *ptr, size_t size, const char *file, int line)
{
	(void)file;
	(void)line;
	allocations++;
	if (size == 0) {
		zero_allocations++;
		free(ptr);
		return NULL;
	}
	return realloc(ptr, size);
}

static void
counted_free(void *ptr)
{
	if (ptr)
		releases++;
	free(ptr);
}

static int
count_line(const git_diff_delta *delta, const git_diff_hunk *hunk,
    const git_diff_line *line, void *payload)
{
	(void)delta;
	(void)hunk;
	(void)line;
	(void)payload;
	lines++;
	return 0;
}

int
main(void)
{
	git_allocator allocator = { counted_malloc, counted_realloc, counted_free };
	git_merge_file_input ancestor, ours, theirs;
	git_merge_file_result result = { 0 };
	const char before[] = "one\ntwo\n";
	const char after[] = "one\nchanged\n";
	int error;

	if (git_libgit2_init() < 0 ||
	    git_libgit2_opts(GIT_OPT_SET_ALLOCATOR, &allocator) < 0)
		return 1;

	error = git_diff_buffers(before, sizeof(before) - 1, "before",
	    after, sizeof(after) - 1, "after", NULL, NULL, NULL, NULL,
	    count_line, NULL);
	if (error < 0 || lines == 0 || allocations == 0)
		return 2;

	/* Clear any stale error using the declared public compatibility API. */
	giterr_clear();
	if (git_error_last()->klass != GIT_ERROR_NONE)
		return 7;

	/* This fixture reaches xdl_init_classifier on its third allocation. */
	allocations = 0;
	fail_xdiff_allocation = 1;
	error = git_diff_buffers(before, sizeof(before) - 1, "before",
	    after, sizeof(after) - 1, "after", NULL, NULL, NULL, NULL,
	    count_line, NULL);
	fail_xdiff_allocation = 0;
	if (!xdiff_failure_hit || error >= 0 || git_error_last()->klass != GIT_ERROR_NOMEMORY) {
		fprintf(stderr, "xdiff allocation error was not propagated (%d)\n", error);
		return 6;
	}

	if (git_merge_file_input_init(&ancestor, GIT_MERGE_FILE_INPUT_VERSION) < 0 ||
	    git_merge_file_input_init(&ours, GIT_MERGE_FILE_INPUT_VERSION) < 0 ||
	    git_merge_file_input_init(&theirs, GIT_MERGE_FILE_INPUT_VERSION) < 0)
		return 3;
	ancestor.ptr = ours.ptr = theirs.ptr = "";
	ancestor.size = ours.size = theirs.size = 0;
	zero_allocations = 0;
	error = git_merge_file(&result, &ancestor, &ours, &theirs, NULL);
	if (error < 0 || result.len != 0 || result.ptr != NULL) {
		fprintf(stderr, "empty merge: error=%d len=%zu ptr=%p zero allocations=%zu\n",
		    error, result.len, (void *)result.ptr, zero_allocations);
		return 4;
	}
	git_merge_file_result_free(&result);
	if (releases == 0)
		return 5;

	git_libgit2_opts(GIT_OPT_SET_ALLOCATOR, NULL);
	git_libgit2_shutdown();
	printf("allocator, xdiff error propagation and empty merge verified\n");
	return 0;
}
