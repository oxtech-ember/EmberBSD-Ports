/*
 * Host test of the swipe state transitions in patch-wscons-swipe-gestures
 * (review Dev Bots #473).  swipe-state.sh extracts the code between the
 * "wscons-swipe-state" markers from the patch itself; the model below
 * calls it the way wscons_process() and wscons_sendevents_set_mode() do.
 * Compile with -DLEGACY for the previous behaviour (disabling a device did
 * not touch the swipe): the cancel-on-disable checks must then fail.
 */
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "swipe-state-extract.h"

static unsigned npass, nfail;
#define CHECK(c) do { if (!(c)) { fprintf(stderr, "FAIL line %d: %s\n", \
    __LINE__, #c); nfail++; } else npass++; } while (0)

/* What libinput would be told: B<n> begin, U update, E end, X end cancelled. */
static char out[64];
static void emit(char c, int n)
{
	size_t l = strlen(out);
	out[l] = c;
	if (n >= 0)
		out[l + 1] = (char)('0' + n);
}

static struct wscons_swipe sw;
static bool disabled;

static void reset(void)
{
	memset(&sw, 0, sizeof(sw));
	memset(out, 0, sizeof(out));
	disabled = false;
}

/* The event cases of wscons_process(), for a device that is not disabled. */
static void ev_begin(int fingers)
{
	int old;

	if (disabled)
		return;		/* wscons_device_dispatch() drains and drops */
	if (wscons_swipe_begin(&sw, fingers, &old))
		emit('X', old);
	emit('B', sw.fingers);
}
static void ev_update(void)
{
	if (!disabled && wscons_swipe_update(&sw))
		emit('U', -1);
}
static void ev_end(bool cancel)
{
	int f;

	if (!disabled && wscons_swipe_close(&sw, &f))
		emit(cancel ? 'X' : 'E', f);
}

/* wscons_sendevents_set_mode(): DISABLED / ENABLED. */
static void set_disabled(bool d)
{
	int f;

	if (d && !disabled) {
#ifndef LEGACY
		if (wscons_swipe_close(&sw, &f))
			emit('X', f);
#else
		(void)f;
#endif
	}
	disabled = d;
}

int main(void)
{
	/* A normal swipe. */
	reset();
	ev_begin(3); ev_update(); ev_update(); ev_end(false);
	CHECK(strcmp(out, "B3UUE3") == 0 && !sw.active);

	/* UPDATE and END outside a swipe are ignored. */
	reset();
	ev_update(); ev_end(false); ev_end(true);
	CHECK(out[0] == 0);

	/* A second BEGIN cancels the first one: pairs stay matched. */
	reset();
	ev_begin(3); ev_begin(4); ev_end(false);
	CHECK(strcmp(out, "B3X3B4E4") == 0);

	/* #473: BEGIN, disabled (END is drained and dropped), enabled, BEGIN. */
	reset();
	ev_begin(3);
	set_disabled(true);
	CHECK(strcmp(out, "B3X3") == 0 && !sw.active);	/* cancelled at once */
	ev_update();					/* drained */
	ev_end(false);					/* drained: END lost */
	set_disabled(false);
	ev_update();					/* stale UPDATE: ignored */
	ev_end(false);					/* stale END: ignored */
	CHECK(strcmp(out, "B3X3") == 0);
	ev_begin(3);
	ev_update();
	ev_end(false);
	CHECK(strcmp(out, "B3X3B3UE3") == 0 && !sw.active);

	/* Disabling an idle device reports nothing. */
	reset();
	set_disabled(true);
	set_disabled(false);
	CHECK(out[0] == 0);

	/* BEGIN while disabled is not recorded: no phantom swipe after enable. */
	reset();
	set_disabled(true);
	ev_begin(3);
	set_disabled(false);
	ev_update();
	ev_end(false);
	CHECK(out[0] == 0 && !sw.active);

	printf("libopeninput swipe state: %u checks passed, %u failed\n", npass, nfail);
	return nfail != 0;
}
