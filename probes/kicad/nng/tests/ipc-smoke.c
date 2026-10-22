/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Test the installed KiCad IPC provider. */

#include <sys/types.h>

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <nng/nng.h>
#include <nng/protocol/reqrep0/rep.h>
#include <nng/protocol/reqrep0/req.h>

static unsigned int passed;

static int
expect_status(const char *operation, int actual, int expected)
{
	if (actual != expected) {
		fprintf(stderr, "%s: got %d (%s), expected %d (%s)\n",
		    operation, actual, nng_strerror(actual), expected,
		    nng_strerror(expected));
		return 0;
	}
	passed++;
	return 1;
}

static int
receive_bytes(nng_socket socket, const void *expected, size_t expected_size)
{
	void *data = NULL;
	size_t size = 0;
	int error, equal;

	error = nng_recv(socket, &data, &size, NNG_FLAG_ALLOC);
	if (error != 0) {
		fprintf(stderr, "receive: %s\n", nng_strerror(error));
		return 0;
	}
	equal = size == expected_size && memcmp(data, expected, size) == 0;
	nng_free(data, size);
	if (!equal) {
		fprintf(stderr, "receive: message bytes or length differ\n");
		return 0;
	}
	passed++;
	return 1;
}

static int
receive_timeout(nng_socket socket)
{
	void *data = NULL;
	size_t size = 0;
	int error;

	error = nng_recv(socket, &data, &size, NNG_FLAG_ALLOC);
	if (error == 0)
		nng_free(data, size);
	return expect_status("receive timeout", error, NNG_ETIMEDOUT);
}

static int
set_deadlines(nng_socket socket)
{
	return expect_status("set receive deadline",
	    nng_socket_set_ms(socket, NNG_OPT_RECVTIMEO, 500), 0) &&
	    expect_status("set send deadline",
	    nng_socket_set_ms(socket, NNG_OPT_SENDTIMEO, 1000), 0);
}

int
main(void)
{
	static unsigned char requests[][8] = {
		{ 0x08, 0x01, 0x00, 0xff, 'K', 'I', 'C', 'A' },
		{ 0x08, 0x02, 'D', 0x00, 0x80, 'I', 'P', 'C' }
	};
	static unsigned char replies[][7] = {
		{ 0x12, 0x05, 'O', 'K', 0x00, 0xff, 0x01 },
		{ 0x12, 0x05, 0x80, 'O', 'K', 0x00, 0x02 }
	};
	nng_socket server = NNG_SOCKET_INITIALIZER;
	nng_socket client = NNG_SOCKET_INITIALIZER;
	nng_listener listener;
	char directory[] = "nng-ipc.XXXXXX";
	char cwd[1024], path[1100], url[1110];
	int server_open = 0, client_open = 0, directory_created = 0;
	int result = EXIT_FAILURE, length;
	size_t i;

	/* Keep the hard bound active through socket and library teardown. */
	alarm(10);
	if (strcmp(nng_version(), "1.12.3") != 0) {
		fprintf(stderr, "expected NNG 1.12.3, got %s\n", nng_version());
		goto out;
	}
	if (getcwd(cwd, sizeof(cwd)) == NULL) {
		perror("getcwd");
		goto out;
	}
	if (mkdtemp(directory) == NULL) {
		perror("mkdtemp");
		goto out;
	}
	directory_created = 1;
	length = snprintf(path, sizeof(path), "%s/%s/socket", cwd, directory);
	/* This conservative bound also fits the shorter BSD sun_path. */
	if (length < 0 || length >= 100) {
		fprintf(stderr, "run from a short private working directory\n");
		goto out;
	}
	length = snprintf(url, sizeof(url), "ipc://%s", path);
	if (length < 0 || (size_t)length >= sizeof(url))
		goto out;

	if (!expect_status("open REP0", nng_rep0_open(&server), 0))
		goto out;
	server_open = 1;
	if (!set_deadlines(server) ||
	    !expect_status("create listener",
	    nng_listener_create(&listener, server, url), 0) ||
	    !expect_status("start listener", nng_listener_start(listener, 0), 0))
		goto out;
	if (!receive_timeout(server) ||
	    !expect_status("REP send before request",
	    nng_send(server, replies[0], sizeof(replies[0]), 0), NNG_ESTATE))
		goto out;

	if (!expect_status("open REQ0", nng_req0_open(&client), 0))
		goto out;
	client_open = 1;
	if (!set_deadlines(client) ||
	    !expect_status("dial IPC", nng_dial(client, url, NULL,
	    NNG_FLAG_NONBLOCK), 0))
		goto out;
	for (i = 0; i < sizeof(requests) / sizeof(requests[0]); i++) {
		if (!expect_status("send request",
		    nng_send(client, requests[i], sizeof(requests[i]), 0), 0) ||
		    !receive_bytes(server, requests[i], sizeof(requests[i])) ||
		    !expect_status("send reply",
		    nng_send(server, replies[i], sizeof(replies[i]), 0), 0) ||
		    !receive_bytes(client, replies[i], sizeof(replies[i])))
			goto out;
	}
	/* A live peer receives the request but deliberately sends no reply. */
	if (!expect_status("set unanswered request deadline",
	    nng_socket_set_ms(client, NNG_OPT_RECVTIMEO, 150), 0) ||
	    !expect_status("send unanswered request",
	    nng_send(client, requests[0], sizeof(requests[0]), 0), 0) ||
	    !receive_bytes(server, requests[0], sizeof(requests[0])) ||
	    !receive_timeout(client))
		goto out;
	result = EXIT_SUCCESS;

out:
	if (client_open && !expect_status("close REQ0", nng_close(client), 0))
		result = EXIT_FAILURE;
	if (server_open && !expect_status("close REP0", nng_close(server), 0))
		result = EXIT_FAILURE;
	nng_fini();
	if (directory_created) {
		/* Construct the owned path only when it fit the IPC length bound. */
		length = snprintf(path, sizeof(path), "%s/socket", directory);
		if (length < 0 || (size_t)length >= sizeof(path)) {
			result = EXIT_FAILURE;
		} else if (unlink(path) != 0 && errno != ENOENT) {
			perror("unlink owned socket");
			result = EXIT_FAILURE;
		}
		if (rmdir(directory) != 0) {
			perror("rmdir owned directory");
			result = EXIT_FAILURE;
		}
	}
	alarm(0);
	if (result == EXIT_SUCCESS)
		printf("PASS: NNG %s IPC REQ0/REP0: %u checks\n",
		    nng_version(), passed);
	return result;
}
