/*
 * Host test of the button pairing rule in patch-wscons-unpaired-buttons
 * (field defect: the pointer moved, the clicks did nothing in all windows).
 * button-pairing.sh extracts the code between the "wscons-button-state"
 * markers from the patch itself.  The model below adds what is around it:
 * the per-seat press count of libinput (update_seat_button_count()), the
 * filter of KWin (a press is taken only with count 1, a release only with
 * count 0) and the button state that the compositor keeps.
 * Compile with -DLEGACY for the previous behaviour: every press was passed
 * on; the checks of a lost release must then fail.
 */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#ifdef LEGACY
#define WSCONS_BUTTON_REPORT	0x1
#define WSCONS_BUTTON_REPAIR	0x2
static unsigned int
wscons_button_step(uint32_t *pressed, unsigned int value, bool down)
{
	if (value >= 32)
		return WSCONS_BUTTON_REPORT;
	if (down) {
		*pressed |= (uint32_t)1 << value;
		return WSCONS_BUTTON_REPORT;
	}
	if (!(*pressed & ((uint32_t)1 << value)))
		return 0;
	*pressed &= ~((uint32_t)1 << value);
	return WSCONS_BUTTON_REPORT;
}
#else
#include "button-state-extract.h"
#endif

static unsigned npass, nfail;
#define CHECK(c) do { if (!(c)) { fprintf(stderr, "FAIL line %d: %s\n", \
    __LINE__, #c); nfail++; } else npass++; } while (0)

enum { LEFT = 0, MIDDLE = 1, RIGHT = 2, NBUTTONS = 3 };

static uint32_t pressed;		/* wscons_device.sendevents.pressed */
static int seat_count[NBUTTONS];	/* libinput_seat.button_count */
static bool held[NBUTTONS];		/* the compositor: button is down */
static unsigned clicks[NBUTTONS];	/* releases the compositor accepted */

static void reset(void)
{
	pressed = 0;
	memset(seat_count, 0, sizeof(seat_count));
	memset(held, 0, sizeof(held));
	memset(clicks, 0, sizeof(clicks));
}

/* pointer_notify_button() and the compositor behind it. */
static void notify(unsigned b, bool down)
{
	int count;

	if (down)
		count = ++seat_count[b];
	else
		count = seat_count[b] == 0 ? 0 : --seat_count[b];
	if ((down && count != 1) || (!down && count != 0))
		return;				/* KWin drops the event */
	held[b] = down;
	if (!down)
		clicks[b]++;
}

/* WSCONS_EVENT_MOUSE_DOWN / _UP in wscons_process(). */
static void ev(unsigned b, bool down)
{
	unsigned int step = wscons_button_step(&pressed, b, down);

	if (step & WSCONS_BUTTON_REPAIR)
		notify(b, false);
	if (step & WSCONS_BUTTON_REPORT)
		notify(b, down);
}

/* wscons_release_buttons(): send-events DISABLED, device removed. */
static void release_all(void)
{
	unsigned b;

	for (b = 0; b < NBUTTONS; b++)
		if (pressed & ((uint32_t)1 << b))
			notify(b, false);
	pressed = 0;
}

static bool any_held(void)
{
	return held[LEFT] || held[MIDDLE] || held[RIGHT];
}

int main(void)
{
	unsigned i;

	/* Ordinary clicks; a button change while the pad button is down. */
	reset();
	ev(LEFT, true); ev(LEFT, false);
	ev(RIGHT, true); ev(LEFT, true); ev(RIGHT, false); ev(LEFT, false);
	CHECK(!any_held() && clicks[LEFT] == 2 && clicks[RIGHT] == 1);
	CHECK(pressed == 0);

	/* A release without a press is dropped. */
	reset();
	ev(RIGHT, false);
	CHECK(!any_held() && clicks[RIGHT] == 0 && seat_count[RIGHT] == 0);

	/*
	 * The release of the right button is lost (not delivered by the
	 * kernel).  The compositor holds the button until the next press of
	 * it; that press repairs the pair and the click works.
	 */
	reset();
	ev(RIGHT, true);			/* its release is lost */
	CHECK(held[RIGHT]);
	ev(RIGHT, true);
	CHECK(held[RIGHT] && seat_count[RIGHT] == 1);
	ev(RIGHT, false);
	CHECK(!any_held());
	CHECK(seat_count[RIGHT] == 0);
	CHECK(clicks[RIGHT] == 2);
	/* All later clicks arrive, and the other buttons are not blocked. */
	for (i = 0; i < 5; i++) {
		ev(RIGHT, true); ev(RIGHT, false);
		ev(LEFT, true); ev(LEFT, false);
	}
	CHECK(!any_held());
	CHECK(clicks[RIGHT] == 7 && clicks[LEFT] == 5);

	/*
	 * The field state: lost release, more clicks of that button, then
	 * the device is disabled and enabled.  Nothing may stay down.
	 */
	reset();
	ev(MIDDLE, true);			/* its release is lost */
	ev(MIDDLE, true); ev(MIDDLE, false);
	ev(MIDDLE, true); ev(MIDDLE, false);
	release_all();
	CHECK(!any_held());
	CHECK(seat_count[MIDDLE] == 0);
	ev(MIDDLE, true); ev(MIDDLE, false);
	CHECK(!any_held() && clicks[MIDDLE] >= 1);

	/* A lost release, then disable: the disable alone releases it. */
	reset();
	ev(LEFT, true);
	release_all();
	CHECK(!any_held() && seat_count[LEFT] == 0);
	ev(LEFT, false);			/* late release: dropped */
	CHECK(seat_count[LEFT] == 0 && clicks[LEFT] == 1);

	/* A device is removed with a button down (release_all on removal). */
	reset();
	ev(LEFT, true);
	release_all();
	CHECK(!any_held());
	/* Another device of the seat still works. */
	pressed = 0;
	ev(LEFT, true); ev(LEFT, false);
	CHECK(!any_held() && clicks[LEFT] == 2);

	/* Buttons outside the mask are passed on unchanged. */
	reset();
	CHECK(wscons_button_step(&pressed, 40, true) == WSCONS_BUTTON_REPORT);
	CHECK(wscons_button_step(&pressed, 40, false) == WSCONS_BUTTON_REPORT);
	CHECK(wscons_button_step(&pressed, (unsigned int)-1, true) ==
	    WSCONS_BUTTON_REPORT);
	CHECK(pressed == 0);

	printf("libopeninput button pairing: %u checks passed, %u failed\n",
	    npass, nfail);
	return nfail != 0;
}
