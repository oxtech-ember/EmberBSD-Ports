/* SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD (AI-assisted). Finite private-process checks; no daemon service.
 */
#include <sys/types.h>
#include <sys/select.h>
#include <sys/wait.h>
#include <assert.h>
#include <signal.h>
#include <stdio.h>
#include <unistd.h>
#include <libdaemon/daemon.h>

int
main(void)
{
	/* The configure cache answer must match this target-header signature. */
	int (*setpgrp_signature)(pid_t, pid_t) = setpgrp;
	assert(setpgrp_signature != NULL);
	alarm(10);
	assert(daemon_retval_init() == 0);
	pid_t pid = fork();
	assert(pid >= 0);
	if (pid == 0) _exit(daemon_retval_send(42) == 0 ? 0 : 1);
	int value = daemon_retval_wait(5);
	int status = 0;
	assert(waitpid(pid, &status, 0) == pid);
	assert(WIFEXITED(status) && WEXITSTATUS(status) == 0);
	assert(value == 42);
	assert(daemon_signal_init(SIGUSR1, 0) == 0);
	int fd = daemon_signal_fd();
	assert(fd >= 0 && fd < FD_SETSIZE);
	assert(kill(getpid(), SIGUSR1) == 0);
	fd_set set;
	FD_ZERO(&set);
	FD_SET(fd, &set);
	struct timeval timeout = { 2, 0 };
	assert(select(fd + 1, &set, NULL, NULL, &timeout) == 1);
	assert(daemon_signal_next() == SIGUSR1);
	assert(daemon_signal_next() == 0);
	daemon_signal_done();
	alarm(0);
	puts("PASS: target setpgrp signature, child return channel and self-signal pipe");
	return 0;
}
