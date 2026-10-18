/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted); real Unix-socket lifecycle contract. */
#include <sys/stat.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <spnav.h>

static int
closed_state(void)
{
	spnav_event event;

	return spnav_fd() == -1 && spnav_close() == -1 &&
	    spnav_poll_event(&event) == 0 && spnav_wait_event(&event) == 0 &&
	    spnav_remove_events(SPNAV_EVENT_ANY) == 0 &&
	    spnav_sensitivity(1.0) == -1;
}

int
main(int argc, char **argv)
{
	spnav_event event;
	struct stat st;
	int i, zero, cycles;

	if (argc != 2)
		return 2;
	if (strcmp(argv[1], "failed-open") == 0) {
		/* Do not contact an unrelated daemon or use its configuration. */
		if (stat("/var/run/spnav.sock", &st) == 0 ||
		    stat("/etc/spnavrc", &st) == 0)
			return 3;
		for (i = 0; i < 4; ++i) {
			if (spnav_open() != -1 || spnav_fd() != -1)
				return 4;
		}
		puts("PASS: four failed connections keep the library closed");
		return 0;
	}
	if (strcmp(argv[1], "closed-state") == 0)
		return closed_state() ? 0 : 5;
	zero = strcmp(argv[1], "fd-zero") == 0 ||
	    strcmp(argv[1], "fd-zero-legacy") == 0;
	if (zero)
		(void)close(STDIN_FILENO);
	if (strcmp(argv[1], "fd-zero-legacy") == 0) {
		if (spnav_open() != 0 || spnav_fd() != STDIN_FILENO ||
		    spnav_protocol() != 0 || spnav_sensitivity(1.25) != 0 ||
		    spnav_close() != 0 || !closed_state())
			return 6;
		puts("PASS: descriptor-zero legacy sensitivity and close");
		return 0;
	}
	if (!zero && strcmp(argv[1], "events") != 0)
		return 7;
	cycles = zero ? 1 : 2;
	for (i = 0; i < cycles; ++i) {
		if (spnav_open() != 0 || spnav_protocol() != 1 ||
		    (zero && spnav_fd() != STDIN_FILENO))
			return 8;
		if (spnav_wait_event(&event) != SPNAV_EVENT_MOTION ||
		    event.motion.x != 11 || event.motion.y != -12 ||
		    event.motion.z != 13 || event.motion.rx != -14 ||
		    event.motion.ry != 15 || event.motion.rz != -16 ||
		    event.motion.period != 17)
			return 9;
		if (spnav_wait_event(&event) != SPNAV_EVENT_BUTTON ||
		    event.button.press != 1 || event.button.bnum != 4)
			return 10;
		if (spnav_wait_event(&event) != 0 || spnav_close() != 0 ||
		    !closed_state())
			return 11;
	}
	puts("PASS: real motion/button values, disconnect, close and reconnect");
	return 0;
}
