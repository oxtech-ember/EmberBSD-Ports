/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted); real protocol peer for the same C client. */
#define _POSIX_C_SOURCE 200809L
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <errno.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static volatile sig_atomic_t timed_out;

static void
deadline(int sig)
{

	(void)sig;
	timed_out = 1;
}

static int
transfer(int fd, void *data, size_t size, int sending)
{
	unsigned char *ptr = data;
	ssize_t count;

	while (size != 0 && !timed_out) {
		count = sending ? write(fd, ptr, size) : read(fd, ptr, size);
		if (count < 0 && errno == EINTR)
			continue;
		if (count <= 0)
			return -1;
		ptr += count;
		size -= (size_t)count;
	}
	return size == 0 ? 0 : -1;
}

int
main(int argc, char **argv)
{
	struct sockaddr_un address;
	struct sigaction action;
	struct stat st;
	int32_t command, motion[8] = { 0, 11, -12, 13, -14, 15, -16, 17 };
	int32_t button[8] = { 1, 4, 0, 0, 0, 0, 0, 0 };
	float sensitivity;
	pid_t child, waited;
	int listener = -1, connection = -1, bound = 0, status = 0;
	int cycles, legacy, i, result = 1;

	_Static_assert(sizeof(float) == 4, "The protocol uses 32-bit floats");
	if (argc != 4 || strlen(argv[3]) >= sizeof(address.sun_path)) {
		fprintf(stderr, "Usage: socket-peer CLIENT MODE NEW_SOCKET_PATH\n");
		return 2;
	}
	if (strcmp(argv[2], "events") != 0 &&
	    strcmp(argv[2], "fd-zero") != 0 &&
	    strcmp(argv[2], "fd-zero-legacy") != 0)
		return 2;
	if (lstat(argv[3], &st) == 0 || errno != ENOENT)
		return 2;
	cycles = strcmp(argv[2], "events") == 0 ? 2 : 1;
	legacy = strcmp(argv[2], "fd-zero-legacy") == 0;
	memset(&address, 0, sizeof(address));
	address.sun_family = AF_UNIX;
#ifdef __NetBSD__
	address.sun_len = sizeof(address);
#endif
	memcpy(address.sun_path, argv[3], strlen(argv[3]) + 1);
	listener = socket(AF_UNIX, SOCK_STREAM, 0);
	if (listener == -1)
		goto done;
	if (bind(listener, (struct sockaddr *)&address, sizeof(address)) == -1)
		goto done;
	bound = 1;
	if (listen(listener, 2) == -1)
		goto done;
	memset(&action, 0, sizeof(action));
	action.sa_handler = deadline;
	if (sigemptyset(&action.sa_mask) == -1 ||
	    sigaction(SIGALRM, &action, NULL) == -1)
		goto done;
	/* A failing client must not terminate the peer before cleanup. */
	if (signal(SIGPIPE, SIG_IGN) == SIG_ERR)
		goto done;
	child = fork();
	if (child == -1)
		goto done;
	if (child == 0) {
		(void)close(listener);
		if (setenv("SPNAV_SOCKET", argv[3], 1) == -1)
			_exit(126);
		execl(argv[1], argv[1], argv[2], (char *)NULL);
		_exit(127);
	}
	(void)alarm(8);
	for (i = 0; i < cycles; ++i) {
		do {
			connection = accept(listener, NULL, NULL);
		} while (connection == -1 && errno == EINTR && !timed_out);
		if (connection == -1 ||
		    transfer(connection, &command, sizeof(command), 0) == -1 ||
		    command != INT32_C(0x7faa5501))
			goto stop_child;
		command = legacy ? INT32_C(0x7faa5500) : INT32_C(0x7faa5501);
		if (transfer(connection, &command, sizeof(command), 1) == -1)
			goto stop_child;
		if (legacy) {
			if (transfer(connection, &sensitivity, sizeof(sensitivity), 0) == -1 ||
			    sensitivity != 1.25f)
				goto stop_child;
		} else if (transfer(connection, motion, sizeof(motion), 1) == -1 ||
		    transfer(connection, button, sizeof(button), 1) == -1) {
			goto stop_child;
		}
		(void)close(connection);
		connection = -1;
	}
	do {
		waited = waitpid(child, &status, 0);
	} while (waited == -1 && errno == EINTR && !timed_out);
	if (waited != child)
		goto stop_child;
	if (WIFEXITED(status) && WEXITSTATUS(status) == 0 && !timed_out)
		result = 0;
	goto done;

stop_child:
	(void)alarm(0);
	(void)kill(child, SIGTERM);
	do {
		waited = waitpid(child, &status, 0);
	} while (waited == -1 && errno == EINTR);
done:
	(void)alarm(0);
	if (connection >= 0)
		(void)close(connection);
	if (listener >= 0)
		(void)close(listener);
	if (bound)
		(void)unlink(argv[3]);
	if (result == 0)
		puts("PASS: real C packet peer and unchanged library client");
	else
		fprintf(stderr, "C packet peer failed: timeout=%d child_status=%d\n",
		    (int)timed_out, status);
	return result;
}
