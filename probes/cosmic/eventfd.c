/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Check the real target eventfd contract. */
#include <sys/types.h>
#include <sys/eventfd.h>

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <unistd.h>

#define CHECK(test) do { if (!(test)) { \
	fprintf(stderr, "FAIL: %s (errno=%d)\n", #test, errno); goto fail; \
} } while (0)

int
main(void)
{
	struct pollfd watch;
	eventfd_t value = 0;
	int fd = -1, semaphore = -1, flags;
	int status = 1;

	fd = eventfd(2, EFD_CLOEXEC | EFD_NONBLOCK);
	CHECK(fd >= 0);
	flags = fcntl(fd, F_GETFD);
	CHECK(flags >= 0 && (flags & FD_CLOEXEC) != 0);
	flags = fcntl(fd, F_GETFL);
	CHECK(flags >= 0 && (flags & O_NONBLOCK) != 0);
	watch = (struct pollfd){ .fd = fd, .events = POLLIN };
	CHECK(poll(&watch, 1, 0) == 1 && (watch.revents & POLLIN) != 0);
	CHECK(eventfd_read(fd, &value) == 0 && value == 2);
	errno = 0;
	CHECK(eventfd_read(fd, &value) == -1 && errno == EAGAIN);
	CHECK(eventfd_write(fd, 3) == 0);
	CHECK(poll(&watch, 1, 0) == 1 && (watch.revents & POLLIN) != 0);
	CHECK(eventfd_read(fd, &value) == 0 && value == 3);
	errno = 0;
	CHECK(eventfd_write(fd, UINT64_MAX) == -1 && errno == EINVAL);
	CHECK(poll(&watch, 1, 0) == 0);
	semaphore = eventfd(2, EFD_SEMAPHORE | EFD_NONBLOCK);
	CHECK(semaphore >= 0);
	CHECK(eventfd_read(semaphore, &value) == 0 && value == 1);
	CHECK(eventfd_read(semaphore, &value) == 0 && value == 1);
	errno = 0;
	CHECK(eventfd_read(semaphore, &value) == -1 && errno == EAGAIN);
	status = 0;
fail:
	if (semaphore >= 0 && close(semaphore) != 0)
		status = 1;
	if (fd >= 0 && close(fd) != 0)
		status = 1;
	if (status == 0)
		puts("PASS: 15 real eventfd counter, polling, flag and semaphore contracts");
	return status;
}
