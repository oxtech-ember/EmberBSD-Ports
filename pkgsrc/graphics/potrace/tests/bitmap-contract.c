/* Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT */
#include <potrace/bitmap.h>
#include <stdio.h>

static void
check(int ok, const char *message)
{

	if (!ok) {
		fprintf(stderr, "FAIL: %s\n", message);
		exit(1);
	}
}

static void
empty_bitmap(int w, int h, const potrace_param_t *param)
{
	potrace_bitmap_t *bm = bm_new(w, h);
	potrace_state_t *state;

	check(bm != NULL, "zero-dimension allocation");
	check(!BM_GET(bm, 0, 0), "zero-dimension read");
	BM_PUT(bm, 0, 0, 1);
	check(!BM_GET(bm, 0, 0), "zero-dimension write stays out of bounds");
	bm_flip(bm);
	state = potrace_trace(param, bm);
	check(state != NULL && state->status == POTRACE_STATUS_OK &&
	    state->plist == NULL, "empty bitmap traces no paths");
	potrace_state_free(state);
	bm_free(bm);
}

int
main(void)
{
	const int w = BM_WORDBITS + 3, h = 4;
	potrace_param_t *param = potrace_param_default();
	potrace_bitmap_t *bm, *copy;
	const potrace_word *allocation;
	potrace_state_t *state;
	int x, y;

	check(param != NULL, "trace parameters");
	empty_bitmap(0, 0, param);
	empty_bitmap(0, 5, param);
	empty_bitmap(5, 0, param);
	bm_free(NULL);
	bm = bm_new(w, h);
	check(bm != NULL, "bitmap allocation");
	allocation = bm_base(bm);
	check(bm->dy == 2, "bitmap spans two words per row");
	for (y = 0; y < h; ++y)
		for (x = 0; x < w; ++x)
			check(!BM_GET(bm, x, y), "bitmap initially clear");
	/* A rectangle crosses the machine-word boundary and is not row symmetric. */
	for (y = 0; y < 2; ++y)
		for (x = BM_WORDBITS - 2; x < BM_WORDBITS + 2; ++x)
			BM_PUT(bm, x, y, 1);
	BM_PUT(bm, -1, 0, 1);
	BM_PUT(bm, w, h, 1);
	check(!BM_GET(bm, -1, 0) && !BM_GET(bm, w, h), "bounded pixel access");
	check(BM_GET(bm, BM_WORDBITS - 1, 0) && BM_GET(bm, BM_WORDBITS, 0),
	    "both sides of word boundary");
	bm_flip(bm);
	check(bm->dy == -2 && bm_base(bm) == allocation, "flipped bitmap owns same allocation");
	check(BM_GET(bm, BM_WORDBITS, h - 1) && !BM_GET(bm, BM_WORDBITS, 0),
	    "flipped rows are addressed through signed stride");
	copy = bm_dup(bm);
	check(copy != NULL && copy->dy > 0, "duplicate a negative-stride bitmap");
	for (y = 0; y < h; ++y)
		for (x = 0; x < w; ++x)
			check(BM_GET(copy, x, y) == BM_GET(bm, x, y), "duplicate pixel contents");
	state = potrace_trace(param, bm);
	check(state != NULL && state->status == POTRACE_STATUS_OK, "trace signed-stride bitmap");
	check(state->plist != NULL && state->plist->next == NULL &&
	    state->plist->area == 8 && state->plist->curve.n > 0, "trace the actual rectangle");
	check(BM_GET(bm, BM_WORDBITS, h - 1), "trace retains caller bitmap");
	potrace_state_free(state);
	bm_free(copy);
	/* This must free bm_base(), not the interior, flipped bm->map pointer. */
	bm_free(bm);
	potrace_param_free(param);
	puts("Installed Potrace bitmap helpers and tracing PASS");
	return 0;
}
