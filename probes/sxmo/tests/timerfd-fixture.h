/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Host-only timerfd contract fixture. */
#ifndef SXMO_TIMERFD_FIXTURE_H
#define SXMO_TIMERFD_FIXTURE_H
#include <stdint.h>
#include <time.h>
#ifdef __APPLE__
struct itimerspec {
	struct timespec it_interval;
	struct timespec it_value;
};
#endif
#define TFD_CLOEXEC 1
#define TFD_TIMER_ABSTIME 2
#define TFD_TIMER_CANCEL_ON_SET 4
int timerfd_create(clockid_t, int);
int timerfd_settime(int, int, const struct itimerspec *, struct itimerspec *);
#endif
