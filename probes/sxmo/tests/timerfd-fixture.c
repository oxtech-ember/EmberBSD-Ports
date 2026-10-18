/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Exercise the real CLI with a ready pipe. */
#include <assert.h>
#include <stdlib.h>
#include <unistd.h>
#include "timerfd-fixture.h"

int
timerfd_create(clockid_t clock_id, int flags)
{
	int descriptors[2];
	uint64_t count = 1;
	const char *selected = getenv("SXMO_TEST_CLOCK");

	assert(selected != NULL);
	assert((int)clock_id == atoi(selected));
	assert(flags == TFD_CLOEXEC);
	assert(pipe(descriptors) == 0);
	assert(write(descriptors[1], &count, sizeof(count)) == sizeof(count));
	assert(close(descriptors[1]) == 0);
	return descriptors[0];
}

int
timerfd_settime(int fd, int flags, const struct itimerspec *value,
    struct itimerspec *old_value)
{
	(void)fd;
	assert(flags == 0);
	assert(old_value == NULL);
	assert(value->it_value.tv_sec == 3);
	assert(value->it_value.tv_nsec == 0);
	assert(value->it_interval.tv_sec == 0);
	assert(value->it_interval.tv_nsec == 0);
	return 0;
}
