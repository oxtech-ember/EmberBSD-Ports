/*
 * Copyright (c) 1988, 1993
 * The Regents of the University of California. All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 * 3. Neither the name of the University nor the names of its contributors
 *    may be used to endorse or promote products derived from this software
 *    without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
 * OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
 * LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
 * OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
 * SUCH DAMAGE.
 */
/*
 * Origin: NetBSD libc system.c 1.28, popen.c 1.38, and
 * OpenBSD libc system.c 1.13. The pipe code derives from Ken Arnold's
 * work published in UNIX Review, Vol. 6, No. 8.
 * EmberBSD adaptation (AI-assisted): opt-in selected shell for nawk.
 * Use fork instead of vfork and retain the caller's signal state on errors.
 */
#ifndef NAWK_COMMAND_SHELL_H
#define NAWK_COMMAND_SHELL_H

#ifndef NAWK_COMMAND_SHELL
#define nawk_system system
#define nawk_popen popen
#define nawk_pclose pclose
#else
#ifndef _NETBSD_SOURCE
#define _NETBSD_SOURCE 1
#endif

#include <sys/types.h>
#include <sys/wait.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

extern char **environ;

static int
nawk_system(const char *command)
{
	struct sigaction ignore, intsave, quitsave;
	sigset_t mask, oldmask;
	pid_t pid;
	int error, status;
	char *const argv[] = { (char *)"sh", (char *)"-c", (char *)"--",
	    (char *)command, NULL };

	if (command == NULL)
		return access(NAWK_COMMAND_SHELL, X_OK) == 0;
	ignore.sa_handler = SIG_IGN;
	ignore.sa_flags = 0;
	sigemptyset(&ignore.sa_mask);
	if (sigaction(SIGINT, &ignore, &intsave) == -1)
		return -1;
	if (sigaction(SIGQUIT, &ignore, &quitsave) == -1) {
		error = errno;
		(void)sigaction(SIGINT, &intsave, NULL);
		errno = error;
		return -1;
	}
	sigemptyset(&mask);
	sigaddset(&mask, SIGCHLD);
	if (sigprocmask(SIG_BLOCK, &mask, &oldmask) == -1) {
		error = errno;
		(void)sigaction(SIGINT, &intsave, NULL);
		(void)sigaction(SIGQUIT, &quitsave, NULL);
		errno = error;
		return -1;
	}

	pid = fork();
	if (pid == 0) {
		if (sigaction(SIGINT, &intsave, NULL) == -1 ||
		    sigaction(SIGQUIT, &quitsave, NULL) == -1 ||
		    sigprocmask(SIG_SETMASK, &oldmask, NULL) == -1)
			_exit(127);
		execve(NAWK_COMMAND_SHELL, argv, environ);
		_exit(127);
	}
	status = -1;
	if (pid != -1) {
		while (waitpid(pid, &status, 0) == -1) {
			if (errno != EINTR) {
				status = -1;
				break;
			}
		}
	}
	error = errno;
	(void)sigaction(SIGINT, &intsave, NULL);
	(void)sigaction(SIGQUIT, &quitsave, NULL);
	(void)sigprocmask(SIG_SETMASK, &oldmask, NULL);
	errno = error;
	return status;
}

#if defined(__NetBSD__)
#define nawk_pclose pclose

static FILE *
nawk_popen(const char *command, const char *type)
{
	char *const argv[] = { (char *)"sh", (char *)"-c", (char *)"--",
	    (char *)command, NULL };

	/* Keep libc's pipe registry so the existing pclose calls stay valid. */
	return popenve(NAWK_COMMAND_SHELL, argv, environ, type);
}
#else
/* nawk is single-threaded. Keep only its selected-shell pipes here. */
static struct nawk_pipe {
	struct nawk_pipe *next;
	FILE *stream;
	pid_t pid;
	int fd;
} *nawk_pipes;

static FILE *
nawk_popen(const char *command, const char *type)
{
	struct nawk_pipe *cur, *old;
	FILE *stream;
	pid_t pid;
	int fds[2], parent, child, target, error;
	char *const argv[] = { (char *)"sh", (char *)"-c", (char *)"--",
	    (char *)command, NULL };

	/* These are the two modes used by awk's input and output pipes. */
	if ((type[0] != 'r' && type[0] != 'w') || type[1] != '\0') {
		errno = EINVAL;
		return NULL;
	}
	if ((cur = malloc(sizeof(*cur))) == NULL)
		return NULL;
	if (pipe(fds) == -1) {
		error = errno;
		free(cur);
		errno = error;
		return NULL;
	}
	parent = type[0] == 'r' ? 0 : 1;
	child = 1 - parent;
	target = type[0] == 'r' ? STDOUT_FILENO : STDIN_FILENO;
	/* Allocate the stream before fork so failure cannot leave a child. */
	if ((stream = fdopen(fds[parent], type)) == NULL) {
		error = errno;
		(void)close(fds[0]);
		(void)close(fds[1]);
		free(cur);
		errno = error;
		return NULL;
	}
	pid = fork();
	if (pid == 0) {
		(void)close(fds[parent]);
		/* POSIX requires previous popen streams to close in this child. */
		for (old = nawk_pipes; old != NULL; old = old->next)
			(void)close(old->fd);
		if (fds[child] != target) {
			if (dup2(fds[child], target) == -1)
				_exit(127);
			(void)close(fds[child]);
		}
		execve(NAWK_COMMAND_SHELL, argv, environ);
		_exit(127);
	}
	error = errno;
	(void)close(fds[child]);
	if (pid == -1) {
		(void)fclose(stream);
		free(cur);
		errno = error;
		return NULL;
	}
	cur->stream = stream;
	cur->pid = pid;
	cur->fd = fds[parent];
	cur->next = nawk_pipes;
	nawk_pipes = cur;
	return stream;
}

static int
nawk_pclose(FILE *stream)
{
	struct nawk_pipe *cur, **link;
	pid_t pid;
	int status;

	for (link = &nawk_pipes; (cur = *link) != NULL; link = &cur->next)
		if (cur->stream == stream)
			break;
	if (cur == NULL) {
		errno = ESRCH;
		return -1;
	}
	*link = cur->next;
	(void)fclose(stream);
	do {
		pid = waitpid(cur->pid, &status, 0);
	} while (pid == -1 && errno == EINTR);
	free(cur);
	return pid == -1 ? -1 : status;
}
#endif
#endif
#endif
