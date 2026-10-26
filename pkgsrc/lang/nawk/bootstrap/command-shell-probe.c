/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Test the actual command-shell header. */
#define _NETBSD_SOURCE 1
#include <sys/types.h>
#include <sys/wait.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define CHECK(test) do { \
	if (!(test)) { \
		fprintf(stderr, "line %d: %s (errno %d)\n", __LINE__, #test, errno); \
		exit(1); \
	} \
} while (0)

#ifdef NAWK_COMMAND_SHELL
static int fail_fork, fail_exec, interrupt_wait, fail_wait, fail_action, fail_mask;
static int fork_calls, pipe_calls, wait_calls, action_calls;

static pid_t
checked_fork(void)
{
	fork_calls++;
	if (fail_fork) {
		errno = EAGAIN;
		return -1;
	}
	return fork();
}

static int
checked_execve(const char *path, char *const argv[], char *const envp[])
{
	if (strcmp(path, NAWK_COMMAND_SHELL) != 0)
		_exit(125);
	if (fail_exec) {
		errno = ENOENT;
		return -1;
	}
	return execve(path, argv, envp);
}

static pid_t
checked_waitpid(pid_t pid, int *status, int options)
{
	struct sigaction sa;
	sigset_t mask;

	wait_calls++;
	CHECK(sigaction(SIGINT, NULL, &sa) == 0 && sa.sa_handler == SIG_IGN);
	CHECK(sigaction(SIGQUIT, NULL, &sa) == 0 && sa.sa_handler == SIG_IGN);
	CHECK(sigprocmask(SIG_BLOCK, NULL, &mask) == 0);
	CHECK(sigismember(&mask, SIGCHLD) == 1);
	if (interrupt_wait) {
		interrupt_wait = 0;
		errno = EINTR;
		return -1;
	}
	if (fail_wait) {
		/* Reap the real child before injecting an unrecoverable wait error. */
		CHECK(waitpid(pid, status, options) == pid);
		errno = ECHILD;
		return -1;
	}
	return waitpid(pid, status, options);
}

static int
checked_sigaction(int signo, const struct sigaction *sa, struct sigaction *old)
{
	action_calls++;
	if (action_calls == fail_action) {
		errno = EINVAL;
		return -1;
	}
	return sigaction(signo, sa, old);
}

static int
checked_sigprocmask(int how, const sigset_t *set, sigset_t *old)
{
	if (fail_mask && how == SIG_BLOCK && set != NULL) {
		errno = EINVAL;
		return -1;
	}
	return sigprocmask(how, set, old);
}

static FILE *
checked_popenve(const char *path, char *const *argv, char *const *envp,
    const char *type)
{
	pipe_calls++;
	CHECK(strcmp(path, NAWK_COMMAND_SHELL) == 0);
	return popenve(path, argv, envp, type);
}

#define fork checked_fork
#define execve checked_execve
#define waitpid checked_waitpid
#define sigaction(...) checked_sigaction(__VA_ARGS__)
#define sigprocmask checked_sigprocmask
#define popenve checked_popenve
#endif
#include "command-shell.h"
#ifdef NAWK_COMMAND_SHELL
#undef fork
#undef execve
#undef waitpid
#undef sigaction
#undef sigprocmask
#undef popenve
#endif

static void
handler(int signo)
{
	(void)signo;
}

static void
check_state(const sigset_t *expected)
{
	struct sigaction sa;
	sigset_t mask;
	int signo;

	CHECK(sigaction(SIGINT, NULL, &sa) == 0 && sa.sa_handler == handler);
	CHECK(sigaction(SIGQUIT, NULL, &sa) == 0 && sa.sa_handler == handler);
	CHECK(sigprocmask(SIG_BLOCK, NULL, &mask) == 0);
	for (signo = 1; signo < NSIG; signo++)
		CHECK(sigismember(&mask, signo) == sigismember(expected, signo));
}

static void
check_exit(int status, int expected)
{
	CHECK(status != -1 && WIFEXITED(status) && WEXITSTATUS(status) == expected);
}

int
main(void)
{
	struct sigaction sa, oldint, oldquit;
	sigset_t mask, oldmask;
	FILE *pipe;
	char text[32];
	int status;

	CHECK(nawk_system(NULL) == 1);
	sigemptyset(&sa.sa_mask);
	sa.sa_flags = 0;
	sa.sa_handler = handler;
	CHECK(sigaction(SIGINT, &sa, &oldint) == 0);
	CHECK(sigaction(SIGQUIT, &sa, &oldquit) == 0);
	CHECK(sigprocmask(SIG_BLOCK, NULL, &oldmask) == 0);
	mask = oldmask;
	sigaddset(&mask, SIGUSR2);
	CHECK(sigprocmask(SIG_SETMASK, &mask, NULL) == 0);

	check_exit(nawk_system(":"), 0);
	check_exit(nawk_system("exit 37"), 37);
	check_exit(nawk_system("exec /nonexistent/nawk-command-test 2>/dev/null"), 127);
	check_state(&mask);
	/* Shell cleanup cannot convert an uncatchable signal to exit(). */
	status = nawk_system("kill -KILL $$");
	CHECK(status != -1 && WIFSIGNALED(status) && WTERMSIG(status) == SIGKILL);
	/* A noninteractive shell cannot trap an inherited ignored SIGINT. */
	check_exit(nawk_system("trap 'exit 73' INT; kill -INT $$; exit 99"), 73);
	check_state(&mask);
	sa.sa_handler = SIG_IGN;
	CHECK(sigaction(SIGINT, &sa, NULL) == 0);
	check_exit(nawk_system("kill -INT $$; exit 0"), 0);
	sa.sa_handler = handler;
	CHECK(sigaction(SIGINT, &sa, NULL) == 0);

	pipe = nawk_popen("printf pipe-input", "r");
	CHECK(pipe != NULL);
	CHECK(fgets(text, sizeof(text), pipe) != NULL && strcmp(text, "pipe-input") == 0);
	check_exit(pclose(pipe), 0);
	pipe = nawk_popen("read value; [ \"$value\" = pipe-output ]", "w");
	CHECK(pipe != NULL);
	CHECK(fputs("pipe-output\n", pipe) >= 0);
	check_exit(pclose(pipe), 0);
	pipe = nawk_popen("exit 23", "r");
	CHECK(pipe != NULL);
	check_exit(pclose(pipe), 23);
	check_state(&mask);

#ifdef NAWK_COMMAND_SHELL
	CHECK(fork_calls == 6 && pipe_calls == 3);
	interrupt_wait = 1;
	wait_calls = 0;
	check_exit(nawk_system("exit 19"), 19);
	CHECK(wait_calls == 2);
	check_state(&mask);
	fail_wait = 1;
	CHECK(nawk_system(":") == -1 && errno == ECHILD);
	fail_wait = 0;
	check_state(&mask);
	fail_exec = 1;
	check_exit(nawk_system(":"), 127);
	fail_exec = 0;
	check_state(&mask);
	fail_fork = 1;
	CHECK(nawk_system(":") == -1 && errno == EAGAIN);
	fail_fork = 0;
	check_state(&mask);
	for (fail_action = 1; fail_action <= 2; fail_action++) {
		action_calls = 0;
		CHECK(nawk_system(":") == -1 && errno == EINVAL);
		check_state(&mask);
	}
	fail_action = 0;
	fail_mask = 1;
	CHECK(nawk_system(":") == -1 && errno == EINVAL);
	fail_mask = 0;
	check_state(&mask);
#endif
	CHECK(sigaction(SIGINT, &oldint, NULL) == 0);
	CHECK(sigaction(SIGQUIT, &oldquit, NULL) == 0);
	CHECK(sigprocmask(SIG_SETMASK, &oldmask, NULL) == 0);
	puts("PASS: nawk command-shell contracts");
	return 0;
}
