/*
 * LD_PRELOAD shim for a PTPd check: append one line to $NTPTRACE_LOG for
 * every call that changes the system clock or the kernel NTP state.
 * ntp_adjtime(2) calls with modes 0 only read the state; they are counted
 * and reported once at exit.
 *
 * SPDX-License-Identifier: BSD-2-Clause
 * AI-assisted (Claude Code, Claude Opus 5.5).
 */

#include <sys/syscall.h>
#include <sys/time.h>
#include <sys/timex.h>

#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

static unsigned long reads;

static void
trace(const char *fmt, ...)
{
	const char *path;
	struct timespec ts;
	va_list ap;
	int fd;

	if ((path = getenv("NTPTRACE_LOG")) == NULL)
		return;
	if ((fd = open(path, O_WRONLY | O_APPEND | O_CREAT, 0644)) == -1)
		return;
	clock_gettime(CLOCK_REALTIME, &ts);
	dprintf(fd, "%lld.%09ld pid=%d ", (long long)ts.tv_sec, ts.tv_nsec,
	    (int)getpid());
	va_start(ap, fmt);
	vdprintf(fd, fmt, ap);
	va_end(ap);
	dprintf(fd, "\n");
	close(fd);
}

int
ntp_adjtime(struct timex *tp)
{
	struct timex req = *tp;
	int ret;

	ret = syscall(SYS_ntp_adjtime, tp);
	if (req.modes == 0) {
		reads++;
		return ret;
	}
	/* The requested values; the kernel overwrites *tp on return. */
	trace("ntp_adjtime modes=0x%x status=0x%x maxerror=%ld esterror=%ld "
	    "constant=%ld freq=%ld ret=%d", req.modes, req.status,
	    req.maxerror, req.esterror, req.constant, req.freq, ret);
	return ret;
}

int
adjtime(const struct timeval *delta, struct timeval *olddelta)
{
	int ret;

	ret = syscall(SYS___adjtime50, delta, olddelta);
	if (delta != NULL)
		trace("adjtime delta=%lld.%06ld ret=%d",
		    (long long)delta->tv_sec, (long)delta->tv_usec, ret);
	return ret;
}

int
settimeofday(const struct timeval *tv, const void *tz)
{
	int ret;

	ret = syscall(SYS___settimeofday50, tv, tz);
	trace("settimeofday ret=%d", ret);
	return ret;
}

int
clock_settime(clockid_t clock, const struct timespec *tp)
{
	int ret;

	ret = syscall(SYS___clock_settime50, clock, tp);
	trace("clock_settime clock=%d ret=%d", (int)clock, ret);
	return ret;
}

static void __attribute__((__destructor__))
report(void)
{
	trace("exit ntp_adjtime_reads=%lu", reads);
}
