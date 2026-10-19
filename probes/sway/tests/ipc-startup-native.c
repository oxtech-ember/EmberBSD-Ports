/* SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD (AI-assisted). Test-only allocator and event/bind boundary.
 * The sandbox forbids native bind(). Use owned files to test socket-path rollback.
 * The injected section uses actual Sway startup/list/log and real descriptor I/O.
 */
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <wayland-server-core.h>
#include "ipc.h"
#include "list.h"
#include "log.h"

struct sway_server {
	struct wl_display *wl_display;
	struct wl_event_loop *wl_event_loop;
};
static struct sway_server server;
static bool terminate_request;
static int exit_value, terminate_calls;
static int allocation, fail_allocation, live_allocations;
static void *allocations[16];
static int publish_call, fail_publish, event_count, listener_count;
static bool fail_event, fail_bind, fail_listen;
static struct wl_list listeners;
struct wl_event_source { unsigned marker; };
struct ipc_client;
int ipc_client_handle_writable(int, uint32_t, void *);
void ipc_client_disconnect(struct ipc_client *);
struct sockaddr_un *ipc_user_sockaddr(void);
int ipc_handle_connection(int, uint32_t, void *);
void ipc_event_shutdown(const char *);
void sway_terminate(int);

static void *
test_malloc(size_t size)
{
	if (++allocation == fail_allocation) {
		errno = ENOMEM;
		return NULL;
	}
	void *result = malloc(size);
	assert(result != NULL && allocation < 16);
	allocations[allocation] = result;
	live_allocations++;
	return result;
}

static void
test_free(void *pointer)
{
	if (!pointer)
		return;
	for (int i = 1; i < 16; i++) {
		if (allocations[i] == pointer) {
			allocations[i] = NULL;
			live_allocations--;
			free(pointer);
			return;
		}
	}
	abort(); /* Reject a double free or ownership violation. */
}

static int
test_setenv(const char *key, const char *value, int overwrite)
{
	if (++publish_call == fail_publish) {
		errno = ENOMEM;
		return -1;
	}
	return setenv(key, value, overwrite);
}

static int
test_bind(int fd, const struct sockaddr *address, socklen_t size)
{
	const struct sockaddr_un *local = (const struct sockaddr_un *)address;
	assert(fcntl(fd, F_GETFD) >= 0 && size == sizeof(*local));
	assert(local->sun_family == AF_UNIX);
	if (fail_bind) {
		errno = ENOTDIR;
		return -1;
	}
	int path = open(local->sun_path, O_CREAT | O_EXCL | O_WRONLY, 0600);
	assert(path >= 0 && close(path) == 0);
	return 0;
}

static int
test_listen(int fd, int backlog)
{
	assert(fcntl(fd, F_GETFD) >= 0 && backlog == 3);
	if (fail_listen) {
		errno = ENOMEM;
		return -1;
	}
	return 0;
}

/* ACTUAL SOURCE */

struct wl_event_source *
wl_event_loop_add_fd(struct wl_event_loop *loop, int fd, uint32_t mask,
    wl_event_loop_fd_func_t callback, void *data)
{
	assert(loop == server.wl_event_loop && data == &server);
	assert(mask == WL_EVENT_READABLE && callback == ipc_handle_connection);
	assert(fcntl(fd, F_GETFD) & FD_CLOEXEC);
	assert(fcntl(fd, F_GETFL) & O_NONBLOCK);
	if (fail_event) {
		errno = ENOMEM;
		return NULL;
	}
	struct wl_event_source *event = malloc(sizeof(*event));
	assert(event != NULL);
	event->marker = 0x1234;
	event_count++;
	return event;
}

int
wl_event_source_remove(struct wl_event_source *event)
{
	assert(event != NULL && event->marker == 0x1234);
	event->marker = 0;
	event_count--;
	free(event);
	return 0;
}

void
wl_display_add_destroy_listener(struct wl_display *display, struct wl_listener *listener)
{
	assert(display == server.wl_display && listener->notify == handle_display_destroy);
	listener_count++;
	wl_list_insert(&listeners, &listener->link);
}

void
wl_display_terminate(struct wl_display *display)
{
	assert(display == server.wl_display);
	terminate_calls++;
}

void
ipc_event_shutdown(const char *reason)
{
	assert(strcmp(reason, "exit") == 0);
	assert(!ipc_has_event_listeners(IPC_EVENT_SHUTDOWN));
}

int
ipc_handle_connection(int fd, uint32_t mask, void *data)
{
	abort(); /* This startup test must never dispatch an incoming connection. */
}

int
main(int argc, char **argv)
{
	char expected[sizeof(((struct sockaddr_un *)0)->sun_path)];
	char long_directory[256];
	bool success;
	int descriptor;

	assert(argc == 3);
	server.wl_display = (struct wl_display *)&server;
	server.wl_event_loop = (struct wl_event_loop *)&listeners;
	wl_list_init(&listeners);
	sway_log_init(SWAY_ERROR, sway_terminate);
	unsetenv("I3SOCK");
	unsetenv("SWAYSOCK");
	assert(setenv("XDG_RUNTIME_DIR", argv[2], 1) == 0);
	assert(snprintf(expected, sizeof(expected), "%s/sway-ipc.%u.%i.sock",
	    argv[2], getuid(), getpid()) < (int)sizeof(expected));
	if (strcmp(argv[1], "before") == 0) {
		sway_terminate(EXIT_FAILURE);
		assert(terminate_request && exit_value == EXIT_FAILURE && terminate_calls == 1);
		return 0;
	}
	if (strncmp(argv[1], "alloc", 5) == 0)
		fail_allocation = atoi(argv[1] + 5);
	fail_event = strcmp(argv[1], "event") == 0;
	if (strncmp(argv[1], "env", 3) == 0)
		fail_publish = atoi(argv[1] + 3);
	if (strcmp(argv[1], "path") == 0) {
		memset(long_directory, 'x', sizeof(long_directory) - 1);
		long_directory[sizeof(long_directory) - 1] = 0;
		assert(setenv("XDG_RUNTIME_DIR", long_directory, 1) == 0);
	}
	fail_bind = strcmp(argv[1], "bind") == 0;
	fail_listen = strcmp(argv[1], "listen") == 0;
#ifdef TEST_BOOL_INIT
	success = ipc_init(&server);
#else
	ipc_init(&server);
	success = ipc_client_list && ipc_client_list->items && ipc_event_source;
#endif
	if (strcmp(argv[1], "success") == 0 || strcmp(argv[1], "after") == 0) {
		assert(success && listener_count == 1 && event_count == 1);
		assert(live_allocations == 3 && ipc_client_list->length == 0);
		assert(strcmp(getenv("SWAYSOCK"), expected) == 0);
		assert(access(expected, F_OK) == 0);
		descriptor = ipc_socket;
		handle_display_destroy(NULL, NULL);
		assert(live_allocations == 0 && event_count == 0 && wl_list_empty(&listeners));
		assert(access(expected, F_OK) == -1 && errno == ENOENT);
		assert(fcntl(descriptor, F_GETFD) == -1 && errno == EBADF);
		if (strcmp(argv[1], "after") == 0) {
			sway_terminate(EXIT_FAILURE);
			assert(terminate_request && terminate_calls == 1);
		}
	} else {
		assert(!success);
		assert(ipc_socket == -1 && ipc_sockaddr == NULL && ipc_client_list == NULL);
		assert(ipc_event_source == NULL && listener_count == 0 && event_count == 0);
		assert(live_allocations == 0 && terminate_calls == 0 && !terminate_request);
		assert(access(expected, F_OK) == -1);
	}
	puts("PASS: actual IPC lifecycle and owned-resource assertions");
	return 0;
}
