/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Appended to actual IPC teardown functions. */
/* Event removal models ownership; all socket I/O and list/log code are real. */
#include <signal.h>

struct wl_event_source {
	unsigned marker;
};

static int event_count;

static struct wl_event_source *
test_event(void)
{
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

int
main(int argc, char **argv)
{
	const char reply[] = "i3-ipc:pending-reply";
	struct ipc_client *client;
	char path[sizeof(((struct sockaddr_un *)0)->sun_path)];
	char input[sizeof(reply)] = { 0 }, fill[4096] = { 0 };
	int pair[2], fd, result = 0;
	ssize_t count;
	size_t filled = 0;

	assert(argc == 3);
	signal(SIGPIPE, SIG_IGN);
	assert(socketpair(AF_UNIX, SOCK_STREAM, 0, pair) == 0);
	assert(fcntl(pair[0], F_SETFL, O_NONBLOCK) == 0);
	assert(snprintf(path, sizeof(path), "%s/ipc.sock", argv[2]) < (int)sizeof(path));
	fd = open(path, O_CREAT | O_EXCL | O_WRONLY, 0600);
	assert(fd >= 0 && close(fd) == 0);
	ipc_socket = socket(AF_UNIX, SOCK_STREAM, 0);
	assert(ipc_socket >= 0);
	ipc_sockaddr = calloc(1, sizeof(*ipc_sockaddr));
	assert(ipc_sockaddr != NULL);
	strcpy(ipc_sockaddr->sun_path, path);
	ipc_event_source = test_event();
	ipc_client_list = create_list();
	assert(ipc_client_list != NULL && ipc_client_list->items != NULL);
	wl_list_init(&ipc_display_destroy.link);
	client = calloc(1, sizeof(*client));
	assert(client != NULL);
	client->fd = pair[0];
	client->event_source = test_event();
	client->writable_event_source = test_event();
	client->write_buffer_size = sizeof(reply);
	client->write_buffer_len = sizeof(reply);
	client->write_buffer = malloc(sizeof(reply));
	assert(client->write_buffer != NULL);
	memcpy(client->write_buffer, reply, sizeof(reply));
	list_add(ipc_client_list, client);
	if (strcmp(argv[1], "closed") == 0) {
		assert(close(pair[1]) == 0);
		pair[1] = -1;
	} else if (strcmp(argv[1], "blocked") == 0) {
		while ((count = write(pair[0], fill, sizeof(fill))) > 0) {
			filled += (size_t)count;
			assert(filled < 16 * 1024 * 1024);
		}
		assert(count == -1 && errno == EAGAIN && filled > 0);
	} else {
		assert(strcmp(argv[1], "reply") == 0);
	}
	handle_display_destroy(NULL, NULL);
	assert(event_count == 0);
	assert(access(path, F_OK) == -1 && errno == ENOENT);
	assert(fcntl(pair[0], F_GETFD) == -1 && errno == EBADF);
	if (strcmp(argv[1], "reply") == 0) {
		count = read(pair[1], input, sizeof(input));
		if (count != sizeof(reply) || memcmp(input, reply, sizeof(reply)) != 0) {
			fputs("FAIL: teardown discarded the pending reply\n", stderr);
			result = 1;
		}
	}
	if (pair[1] >= 0)
		assert(close(pair[1]) == 0);
	return result;
}
