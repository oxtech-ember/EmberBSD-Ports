/* Origin: EmberBSD; AI-assisted foreign ELF ABI probe. */
/* SPDX-License-Identifier: BSD-2-Clause */

#define _POSIX_C_SOURCE 200809L
#include <sys/types.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

static int
number(const char *text, unsigned long max, unsigned long *value)
{
	char *end;

	errno = 0;
	*value = strtoul(text, &end, 10);
	return errno == 0 && end != text && *end == '\0' && *value <= max;
}

static void
stop_child(pid_t pid)
{
	(void)kill(pid, SIGKILL);
	while (waitpid(pid, NULL, 0) == -1 && errno == EINTR)
		/* Retry an interrupted wait. */
		;
}

int
main(int argc, char **argv)
{
	struct timespec start, now, pause = {0, 20000000};
	unsigned long seconds, mib;
	pid_t child;
	int status;

	if (geteuid() == 0)
		return 77;
	if (argc < 4 || !number(argv[1], 30, &seconds) || seconds == 0 ||
	    !number(argv[2], 4096, &mib) || (mib != 0 && mib < 64))
		return 64;
	if (clock_gettime(CLOCK_MONOTONIC, &start) == -1)
		return 75;
	/* Keep the child waitable even if the caller ignored SIGCHLD. */
	if (signal(SIGCHLD, SIG_DFL) == SIG_ERR)
		return 75;
	child = fork();
	if (child == -1)
		return 75;
	if (child == 0) {
		struct rlimit limit = {0, 0};

		if (setrlimit(RLIMIT_CORE, &limit) == -1)
			_exit(77);
		limit.rlim_cur = limit.rlim_max = (rlim_t)seconds;
		if (setrlimit(RLIMIT_CPU, &limit) == -1)
			_exit(77);
		if (mib != 0) {
			limit.rlim_cur = limit.rlim_max = (rlim_t)mib * 1024 * 1024;
			if (setrlimit(RLIMIT_AS, &limit) == -1)
				_exit(77);
		}
		execv(argv[3], &argv[3]);
		perror("execv");
		_exit(75);
	}
	for (;;) {
		pid_t result = waitpid(child, &status, WNOHANG);
		if (result == child) {
			if (WIFEXITED(status))
				return WEXITSTATUS(status);
			return WIFSIGNALED(status) ? 128 + WTERMSIG(status) : 75;
		}
		if (result == -1 && errno != EINTR) {
			if (errno != ECHILD)
				stop_child(child);
			return 75;
		}
		if (clock_gettime(CLOCK_MONOTONIC, &now) == -1) {
			stop_child(child);
			return 75;
		}
		if (now.tv_sec - start.tv_sec >= (time_t)(seconds + 5)) {
			stop_child(child);
			fprintf(stderr, "probe wall timeout\n");
			return 124;
		}
		(void)nanosleep(&pause, NULL);
	}
}
