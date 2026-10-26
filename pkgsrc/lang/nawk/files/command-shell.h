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
 * Origin: NetBSD libc system.c 1.28 and OpenBSD libc system.c 1.13.
 * EmberBSD adaptation (AI-assisted): opt-in selected shell for nawk.
 * Use fork instead of vfork and retain the caller's signal state on errors.
 */
#ifndef NAWK_COMMAND_SHELL_H
#define NAWK_COMMAND_SHELL_H

#ifndef NAWK_COMMAND_SHELL
#define nawk_system system
#define nawk_popen popen
#else
#if !defined(__NetBSD__)
#error "NAWK_COMMAND_SHELL requires NetBSD popenve"
#endif

#ifndef _NETBSD_SOURCE
#define _NETBSD_SOURCE 1
#endif

#include <sys/types.h>
#include <sys/wait.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
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

static FILE *
nawk_popen(const char *command, const char *type)
{
	char *const argv[] = { (char *)"sh", (char *)"-c", (char *)"--",
	    (char *)command, NULL };

	/* Keep libc's pipe registry so the existing pclose calls stay valid. */
	return popenve(NAWK_COMMAND_SHELL, argv, environ, type);
}
#endif
#endif
