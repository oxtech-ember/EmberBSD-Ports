/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted), real peer-credential regression. */
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "egg-unix-credentials.h"

static void
check(int condition, const char *message)
{
	if (!condition) {
		fprintf(stderr, "FAIL: %s\n", message);
		exit(1);
	}
}

int
main(void)
{
	int sockets[2], option;
	socklen_t len;
	pid_t pid;
	uid_t uid;
	unsigned cycle;
	char invalid = 'x';

	for (cycle = 0; cycle != 32; cycle++) {
		check(socketpair(AF_UNIX, SOCK_STREAM, 0, sockets) == 0,
		    "create local stream");
		check(egg_unix_credentials_setup(sockets[0]) == 0,
		    "setup receiver");
		option = -1;
		len = sizeof(option);
		check(getsockopt(sockets[0], SOL_LOCAL, LOCAL_CREDS,
		    &option, &len) == 0 && option == 0,
		    "ancillary credential delivery stays disabled");
		check(egg_unix_credentials_write(sockets[1]) == 0,
		    "write credentials marker");
		check(egg_unix_credentials_read(sockets[0], &pid, &uid) == 0,
		    "read kernel credentials");
		check(pid == getpid() && uid == geteuid(),
		    "kernel peer PID and effective UID match");
		check(write(sockets[1], &invalid, 1) == 1,
		    "write invalid marker");
		check(egg_unix_credentials_read(sockets[0], &pid, &uid) == -1,
		    "reject invalid marker");
		close(sockets[1]);
		check(egg_unix_credentials_read(sockets[0], &pid, &uid) == -1,
		    "reject disconnected peer");
		close(sockets[0]);
	}
	check(egg_unix_credentials_read(-1, &pid, &uid) == -1,
	    "reject invalid descriptor");
	puts("PASS: 32 real peer-credential cycles, markers, EOF and invalid descriptor");
	return 0;
}
