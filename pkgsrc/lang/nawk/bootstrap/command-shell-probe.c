/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Test the actual command-shell header. */
#define _NETBSD_SOURCE 1
#include <sys/types.h>
#include <sys/wait.h>
#include <errno.h>
#include <fcntl.h>
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
static int checking_system = 1;
#if !defined(__NetBSD__)
static int fail_pipe, fail_fdopen, fail_malloc, fail_dup2, allocations;
static int inherited_fd = -1;
static int last_pipe[2] = { -1, -1 };
#endif

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
#if !defined(__NetBSD__)
	if (inherited_fd >= 0 && (fcntl(inherited_fd, F_GETFD) != -1 || errno != EBADF))
		_exit(124);
#endif
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
	if (checking_system) {
		CHECK(sigaction(SIGINT, NULL, &sa) == 0 && sa.sa_handler == SIG_IGN);
		CHECK(sigaction(SIGQUIT, NULL, &sa) == 0 && sa.sa_handler == SIG_IGN);
		CHECK(sigprocmask(SIG_BLOCK, NULL, &mask) == 0);
		CHECK(sigismember(&mask, SIGCHLD) == 1);
	}
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

#if defined(__NetBSD__)
static FILE *
checked_popenve(const char *path, char *const *argv, char *const *envp,
    const char *type)
{
	pipe_calls++;
	CHECK(strcmp(path, NAWK_COMMAND_SHELL) == 0);
	return popenve(path, argv, envp, type);
}
#else
static int
checked_pipe(int fds[2])
{
	int result;

	pipe_calls++;
	if (fail_pipe) {
		errno = EMFILE;
		return -1;
	}
	result = pipe(fds);
	if (result == 0) {
		last_pipe[0] = fds[0];
		last_pipe[1] = fds[1];
	}
	return result;
}

static FILE *
checked_fdopen(int fd, const char *type)
{
	if (fail_fdopen) {
		errno = ENOMEM;
		return NULL;
	}
	return fdopen(fd, type);
}

static void *
checked_malloc(size_t size)
{
	void *result;

	if (fail_malloc) {
		errno = ENOMEM;
		return NULL;
	}
	result = malloc(size);
	if (result != NULL)
		allocations++;
	return result;
}

static void
checked_free(void *pointer)
{
	if (pointer != NULL)
		allocations--;
	free(pointer);
}

static int
checked_dup2(int from, int to)
{
	if (fail_dup2) {
		errno = EBADF;
		return -1;
	}
	return dup2(from, to);
}

#define pipe checked_pipe
#define fdopen checked_fdopen
#define malloc checked_malloc
#define free checked_free
#define dup2 checked_dup2
#endif

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
#undef pipe
#undef fdopen
#undef malloc
#undef free
#undef dup2
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

#if defined(NAWK_COMMAND_SHELL) && !defined(__NetBSD__)
static void
check_pipe_resources(void)
{
	CHECK(allocations == 0 && nawk_pipes == NULL);
	for (int i = 0; i < 2; i++)
		if (last_pipe[i] >= 0)
			CHECK(fcntl(last_pipe[i], F_GETFD) == -1 && errno == EBADF);
}

static void
check_posix_pipes(void)
{
	FILE *stream, *other;
	char text[32];
	pid_t pid;
	int status;

	checking_system = 0;
	CHECK(nawk_popen(":", "r+") == NULL && errno == EINVAL);
	fail_malloc = 1;
	CHECK(nawk_popen(":", "r") == NULL && errno == ENOMEM);
	fail_malloc = 0;
	check_pipe_resources();
	fail_pipe = 1;
	CHECK(nawk_popen(":", "r") == NULL && errno == EMFILE);
	fail_pipe = 0;
	check_pipe_resources();
	fail_fdopen = 1;
	CHECK(nawk_popen(":", "r") == NULL && errno == ENOMEM);
	fail_fdopen = 0;
	check_pipe_resources();
	fail_fork = 1;
	CHECK(nawk_popen(":", "w") == NULL && errno == EAGAIN);
	fail_fork = 0;
	check_pipe_resources();
	fail_exec = 1;
	stream = nawk_popen(":", "r");
	CHECK(stream != NULL);
	check_exit(nawk_pclose(stream), 127);
	fail_exec = 0;
	check_pipe_resources();
	fail_dup2 = 1;
	stream = nawk_popen(":", "r");
	CHECK(stream != NULL);
	check_exit(nawk_pclose(stream), 127);
	fail_dup2 = 0;
	check_pipe_resources();
	stream = nawk_popen("exit 37", "r");
	CHECK(stream != NULL);
	interrupt_wait = 1;
	wait_calls = 0;
	check_exit(nawk_pclose(stream), 37);
	CHECK(wait_calls == 2);
	check_pipe_resources();
	stream = nawk_popen(":", "r");
	CHECK(stream != NULL);
	fail_wait = 1;
	CHECK(nawk_pclose(stream) == -1 && errno == ECHILD);
	fail_wait = 0;
	check_pipe_resources();
	stream = tmpfile();
	CHECK(stream != NULL);
	CHECK(nawk_pclose(stream) == -1 && errno == ESRCH);
	CHECK(fputs("still open", stream) >= 0 && fclose(stream) == 0);
	stream = nawk_popen("read value; [ \"$value\" = first ]", "w");
	CHECK(stream != NULL);
	inherited_fd = fileno(stream);
	other = nawk_popen("echo second", "r");
	CHECK(other != NULL);
	inherited_fd = -1;
	CHECK(fgets(text, sizeof(text), other) != NULL && strcmp(text, "second\n") == 0);
	CHECK(fputs("first\n", stream) >= 0);
	check_exit(nawk_pclose(stream), 0);
	check_exit(nawk_pclose(other), 0);
	check_pipe_resources();
	/* Closed standard descriptors must not break the pipe's dup2 route. */
	pid = fork();
	CHECK(pid != -1);
	if (pid == 0) {
		CHECK(close(STDIN_FILENO) == 0 && close(STDOUT_FILENO) == 0);
		stream = nawk_popen("echo fd-route", "r");
		CHECK(stream != NULL);
		CHECK(fgets(text, sizeof(text), stream) != NULL && strcmp(text, "fd-route\n") == 0);
		check_exit(nawk_pclose(stream), 0);
		check_pipe_resources();
		_exit(0);
	}
	CHECK(waitpid(pid, &status, 0) == pid);
	check_exit(status, 0);
	CHECK(waitpid(-1, &status, WNOHANG) == -1 && errno == ECHILD);
}
#endif

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
	/* popen/pclose preserve the caller's signal dispositions and mask. */
#ifdef NAWK_COMMAND_SHELL
	checking_system = 0;
#endif

	pipe = nawk_popen("echo pipe-input", "r");
	CHECK(pipe != NULL);
	CHECK(fgets(text, sizeof(text), pipe) != NULL && strcmp(text, "pipe-input\n") == 0);
	check_exit(nawk_pclose(pipe), 0);
	pipe = nawk_popen("read value; [ \"$value\" = pipe-output ]", "w");
	CHECK(pipe != NULL);
	CHECK(fputs("pipe-output\n", pipe) >= 0);
	check_exit(nawk_pclose(pipe), 0);
	pipe = nawk_popen("exit 23", "r");
	CHECK(pipe != NULL);
	check_exit(nawk_pclose(pipe), 23);
	check_state(&mask);

#ifdef NAWK_COMMAND_SHELL
	CHECK(fork_calls ==
#if defined(__NetBSD__)
	    6
#else
	    9
#endif
	    && pipe_calls == 3);
	checking_system = 1;
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
#if !defined(__NetBSD__)
	check_posix_pipes();
	check_state(&mask);
#endif
#endif
	CHECK(sigaction(SIGINT, &oldint, NULL) == 0);
	CHECK(sigaction(SIGQUIT, &oldquit, NULL) == 0);
	CHECK(sigprocmask(SIG_SETMASK, &oldmask, NULL) == 0);
	puts("PASS: nawk command-shell contracts");
	return 0;
}
