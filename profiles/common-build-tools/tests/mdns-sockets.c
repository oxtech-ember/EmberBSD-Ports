/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted), real daemon startup error-path contract. */
#include <sys/types.h>
#include <sys/socket.h>
#include <assert.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include "mDNSEmbeddedAPI.h"
#include "dnssd_ipc.h"
#include "uds_daemon.h"

enum fault { SOCKET, BIND, GETFLAGS, SETFLAGS, LISTEN, EVENTLOOP };
static enum fault selected;
static int created = -1;
static unsigned failures, cases, later_calls, fault_calls;

int __real_socket(int, int, int);
int __real_bind(int, const struct sockaddr *, socklen_t);
int __real_fcntl(int, int, ...);
int __real_listen(int, int);

int
__wrap_socket(int domain, int type, int protocol)
{

	if (selected == SOCKET) {
		fault_calls++;
		errno = EMFILE;
		return -1;
	}
	created = __real_socket(domain, type, protocol);
	return created;
}

int
__wrap_bind(int fd, const struct sockaddr *address, socklen_t length)
{

	if (selected == BIND) {
		fault_calls++;
		errno = EACCES;
		return -1;
	}
	return __real_bind(fd, address, length);
}

int
__wrap_fcntl(int fd, int command, ...)
{
	va_list ap;
	int argument;

	assert(command == F_GETFL || command == F_SETFL);
	va_start(ap, command);
	argument = va_arg(ap, int);
	va_end(ap);
	if ((selected == GETFLAGS && command == F_GETFL) ||
	    (selected == SETFLAGS && command == F_SETFL)) {
		fault_calls++;
		errno = EIO;
		return -1;
	}
	if (selected == GETFLAGS && command == F_SETFL)
		later_calls++;
	return __real_fcntl(fd, command, argument);
}

int
__wrap_listen(int fd, int backlog)
{

	if (selected == GETFLAGS)
		later_calls++;
	if (selected == LISTEN) {
		fault_calls++;
		errno = EIO;
		return -1;
	}
	return __real_listen(fd, backlog);
}

mStatus
__wrap_udsSupportAddFDToEventLoop(int fd, udsEventCallback callback,
    void *context, void **platform_data)
{

	(void)fd;
	(void)callback;
	(void)context;
	(void)platform_data;
	/* Every test must stop before starting a service or installing an event. */
	assert(selected == EVENTLOOP || selected == GETFLAGS);
	if (selected == GETFLAGS)
		later_calls++;
	else
		fault_calls++;
	return mStatus_UnknownErr;
}

static unsigned
fd_count(void)
{
	DIR *directory = opendir("/proc/self/fd");
	struct dirent *entry;
	unsigned count = 0;

	assert(directory != NULL);
	while ((entry = readdir(directory)) != NULL)
		if (entry->d_name[0] != '.')
			count++;
	assert(closedir(directory) == 0);
	return count;
}

static int
fd_open(int fd)
{
	char path[64];
	int result;

	assert(snprintf(path, sizeof(path), "/proc/self/fd/%d", fd) > 0);
	result = access(path, F_OK);
	assert(result == 0 || errno == ENOENT);
	return result == 0;
}

static void
check(int condition, const char *message, int external)
{

	if (!condition) {
		fprintf(stderr, "FAIL: fault=%d external=%d: %s\n",
		    selected, external, message);
		failures++;
	}
}

int
main(void)
{
	for (selected = SOCKET; selected <= EVENTLOOP; selected++) {
		for (int external = 0; external < 2; external++) {
			int fd = -1;
			unsigned before = fd_count();

			if (external && (selected == SOCKET || selected == BIND))
				continue;
			if (external) {
				struct sockaddr_un address = { .sun_family = AF_UNIX };

				fd = __real_socket(AF_UNIX, SOCK_STREAM, 0);
				assert(fd >= 0);
				assert(strlen(MDNS_UDS_SERVERPATH) < sizeof(address.sun_path));
				strcpy(address.sun_path, MDNS_UDS_SERVERPATH);
				assert(__real_bind(fd, (struct sockaddr *)&address,
				    sizeof(address)) == 0);
			}
			created = -1;
			later_calls = 0;
			fault_calls = 0;
			check(udsserver_init(external ? &fd : NULL,
			    external ? 1 : 0) == -1, "startup must fail", external);
			if (external) {
				check(__real_fcntl(fd, F_GETFD) >= 0,
				    "caller still owns its descriptor", external);
				assert(close(fd) == 0);
			} else if (created >= 0) {
				check(!fd_open(created),
				    "fresh descriptor must close", external);
			}
			check(fd_count() == before, "descriptor count must match", external);
			check(later_calls == 0, "stop after F_GETFL failure", external);
			check(fault_calls == 1, "selected failure must execute once", external);
			/* Clean a leaking control so later cases remain independent. */
			if (!external && created >= 0 && fd_open(created))
				assert(close(created) == 0);
			assert(unlink(MDNS_UDS_SERVERPATH) == 0 || errno == ENOENT);
			assert(unlink(PID_FILE) == 0 || errno == ENOENT);
			cases++;
		}
	}
	printf("%s: %u real daemon startup error cases; %u failures.\n",
	    failures ? "FAIL" : "PASS", cases, failures);
	return failures ? 1 : 0;
}
