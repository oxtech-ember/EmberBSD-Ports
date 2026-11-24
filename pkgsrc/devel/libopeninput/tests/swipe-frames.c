/* SPDX-License-Identifier: BSD-2-Clause */
/*
 * Host test of wscons_swipe_step_ends().  The model below follows
 * wscons_process() and wscons_device_dispatch(): an event that ends the
 * step flushes the pending X/Y first, X/Y events add to the step, and the
 * end of each read flushes what is left.
 */
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#define WSCONS_EVENT_GESTURE_SWIPE_BEGIN	18
#define WSCONS_EVENT_GESTURE_SWIPE_UPDATE_X	19
#define WSCONS_EVENT_GESTURE_SWIPE_UPDATE_Y	20
#define WSCONS_EVENT_GESTURE_SWIPE_END		21

#include "swipe-frame-extract.h"

enum { B = WSCONS_EVENT_GESTURE_SWIPE_BEGIN, X = WSCONS_EVENT_GESTURE_SWIPE_UPDATE_X,
    Y = WSCONS_EVENT_GESTURE_SWIPE_UPDATE_Y, E = WSCONS_EVENT_GESTURE_SWIPE_END };

static unsigned failures;

/* Output: 'B', 'E', or 'u' for an update with X only, 'v' Y only, 'w' both. */
static char outbuf[64];
static bool has_x, has_y;

static void
flush(void)
{
	char c[2] = { 0, 0 };

	if (!has_x && !has_y)
		return;
	c[0] = has_x && has_y ? 'w' : has_x ? 'u' : 'v';
	strcat(outbuf, c);
	has_x = has_y = false;
}

static void
dispatch(const unsigned *ev, size_t n)
{
	size_t i;

	for (i = 0; i < n; i++) {
		if (wscons_swipe_step_ends(ev[i], has_x, has_y))
			flush();
		if (ev[i] == X)
			has_x = true;
		else if (ev[i] == Y)
			has_y = true;
		else
			strcat(outbuf, ev[i] == B ? "B" : "E");
	}
	flush();
}

static void
check(const char *name, const unsigned *ev, size_t n, size_t split,
    const char *want)
{
	outbuf[0] = '\0';
	has_x = has_y = false;
	dispatch(ev, split);
	dispatch(ev + split, n - split);
	if (strcmp(outbuf, want) != 0) {
		printf("FAIL %s: got %s, want %s\n", name, outbuf, want);
		failures++;
	}
}

#define CHECK(name, split, want, ...) do {				\
	const unsigned ev[] = { __VA_ARGS__ };				\
	check(name, ev, sizeof(ev) / sizeof(ev[0]), split, want);	\
} while (0)

int
main(void)
{
	CHECK("x and y are one update", 0, "BwwE", B, X, Y, X, Y, E);
	CHECK("y then x are one update", 0, "BwE", B, Y, X, E);
	CHECK("two x are two updates", 0, "BuuE", B, X, X, E);
	CHECK("x only before the end", 0, "BuE", B, X, E);
	CHECK("a repeated y starts the next step", 0, "BwwvE", B, X, Y, Y, X, Y, E);
	CHECK("a read ends after x", 2, "BuvE", B, X, Y, E);
	CHECK("a read ends after a full step", 3, "BwwE", B, X, Y, X, Y, E);
	if (failures != 0)
		return 1;
	printf("swipe frames: 7 checks passed\n");
	return 0;
}
