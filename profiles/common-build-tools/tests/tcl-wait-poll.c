/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Exercise the actual Unix wait function. */
#include <sys/time.h>
#include <errno.h>
#include <limits.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <tcl.h>

struct wait_case {
	const char *name;
	int timeout, mask, result, polls, times;
	int poll_timeout[4], poll_result[4];
	short revents[4];
	long long time[3];
};

static const struct wait_case cases[] = {
	{ "indefinite-eintr", -1, TCL_READABLE, TCL_READABLE, 4, 0,
	  { -1, -1, -1, -1 }, { -1, -1, -1, 1 }, { 0, 0, 0, POLLIN }, { 0 } },
	{ "negative-eintr", -2, TCL_READABLE, TCL_READABLE, 2, 0,
	  { -1, -1 }, { -1, 1 }, { 0, POLLIN }, { 0 } },
	{ "zero-empty", 0, TCL_READABLE, 0, 1, 0,
	  { 0 }, { 0 }, { 0 }, { 0 } },
	{ "zero-ready", 0, TCL_READABLE, TCL_READABLE, 1, 0,
	  { 0 }, { 1 }, { POLLIN }, { 0 } },
	{ "read-ready", 500, TCL_READABLE, TCL_READABLE, 1, 1,
	  { 500 }, { 1 }, { POLLIN }, { 1000000 } },
	{ "write-ready", 500, TCL_WRITABLE, TCL_WRITABLE, 1, 1,
	  { 500 }, { 1 }, { POLLOUT }, { 1000000 } },
	{ "exception-ready", 500, TCL_EXCEPTION, TCL_EXCEPTION, 1, 1,
	  { 500 }, { 1 }, { POLLERR }, { 1000000 } },
	{ "finite-eintr-expiry", 500, TCL_READABLE, 0, 2, 3,
	  { 500, 250 }, { -1, 0 }, { 0 }, { 1000000, 1250000, 1500000 } },
	{ "large-safe", 2147483, TCL_READABLE, TCL_READABLE, 1, 1,
	  { 2147483 }, { 1 }, { POLLIN }, { 1000000 } },
	{ "large-overflow", 2147484, TCL_READABLE, TCL_READABLE, 1, 1,
	  { 2147484 }, { 1 }, { POLLIN }, { 1000000 } },
	{ "int-max", INT_MAX, TCL_READABLE, TCL_READABLE, 1, 1,
	  { INT_MAX }, { 1 }, { POLLIN }, { 1000000 } },
};
static const struct wait_case *current;
static int poll_count, time_count;

static long long
fixture_time(void)
{
	if (time_count >= current->times) {
		fprintf(stderr, "%s: unexpected clock call\n", current->name);
		exit(1);
	}
	return current->time[time_count++];
}

static int
fixture_poll(struct pollfd *fds, nfds_t count, int timeout)
{
	int index = poll_count++;
	short events = 0;

	if (current->mask & TCL_READABLE)
		events |= POLLIN | POLLHUP;
	if (current->mask & TCL_WRITABLE)
		events |= POLLOUT;
	if (current->mask & TCL_EXCEPTION)
		events |= POLLERR;
	if (index >= current->polls || count != 1 || fds[0].fd != 42 ||
	    fds[0].events != events || timeout != current->poll_timeout[index]) {
		fprintf(stderr, "%s: unexpected poll call %d, timeout %d\n",
		    current->name, poll_count, timeout);
		exit(1);
	}
	fds[0].revents = current->revents[index];
	if (current->poll_result[index] == -1)
		errno = EINTR;
	return current->poll_result[index];
}

#define poll fixture_poll
#define Tcl_GetDayTime fixture_time
#include "tcl-wait-function.inc"
#undef Tcl_GetDayTime
#undef poll

int
main(int argc, char **argv)
{
	size_t index;
	int result;

	if (argc != 2)
		return 2;
	for (index = 0; index < sizeof(cases) / sizeof(cases[0]); index++) {
		if (strcmp(argv[1], cases[index].name) == 0) {
			current = &cases[index];
			break;
		}
	}
	if (current == NULL)
		return 2;
	result = TclUnixWaitForFile(42, current->mask, current->timeout);
	if (result != current->result || poll_count != current->polls ||
	    time_count != current->times) {
		fprintf(stderr, "%s: result=%d polls=%d clocks=%d\n",
		    current->name, result, poll_count, time_count);
		return 1;
	}
	printf("PASS %s\n", current->name);
	return 0;
}
