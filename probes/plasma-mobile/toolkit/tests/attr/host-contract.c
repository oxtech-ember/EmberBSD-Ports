/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Test the real private xattrat backend. */
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "xattrat_compat.h"

static int method, calls, injected_error, fail_chdir, chdirs, seen_fd;
static int requested_flags, seen_flags;
static const char *seen_name, *seen_value;
static size_t seen_size;
static char value_buffer[8];
static char seen_path[PATH_MAX], seen_cwd[PATH_MAX];

int
attr_test_fchdir(int fd)
{
	if (++chdirs == fail_chdir) {
		errno = EACCES;
		return -1;
	}
	return fchdir(fd);
}

static ssize_t
record(int kind, int fd, const char *path)
{
	method = kind;
	seen_fd = fd;
	calls++;
	assert(getcwd(seen_cwd, sizeof(seen_cwd)) != NULL);
	snprintf(seen_path, sizeof(seen_path), "%s", path ? path : "<fd>");
	errno = injected_error;
	return injected_error ? -1 : 7;
}

#define GET(F, K) ssize_t F(const char *p, const char *n, void *v, size_t s) \
{ seen_name = n; seen_size = s; assert(v == value_buffer); return record(K, -1, p); }
#define SET(F, K) int F(const char *p, const char *n, const void *v, size_t s, int f) \
{ seen_name = n; seen_value = v; seen_size = s; seen_flags = f; return (int)record(K, -1, p); }
#define LIST(F, K) ssize_t F(const char *p, char *v, size_t s) \
{ seen_size = s; assert(v == value_buffer); return record(K, -1, p); }
#define REMOVE(F, K) int F(const char *p, const char *n) \
{ seen_name = n; return (int)record(K, -1, p); }
GET(getxattr, 1)
GET(lgetxattr, 2)
SET(setxattr, 1)
SET(lsetxattr, 2)
LIST(listxattr, 1)
LIST(llistxattr, 2)
REMOVE(removexattr, 1)
REMOVE(lremovexattr, 2)
ssize_t fgetxattr(int fd, const char *n, void *v, size_t s)
{ seen_name = n; seen_size = s; assert(v == value_buffer); return record(3, fd, NULL); }
int fsetxattr(int fd, const char *n, const void *v, size_t s, int f)
{ seen_name = n; seen_value = v; seen_size = s; seen_flags = f; return (int)record(3, fd, NULL); }
ssize_t flistxattr(int fd, char *v, size_t s)
{ seen_size = s; assert(v == value_buffer); return record(3, fd, NULL); }
int fremovexattr(int fd, const char *n)
{ seen_name = n; return (int)record(3, fd, NULL); }

static ssize_t
invoke(int op, int fd, const char *path, int flags)
{
	switch (op) {
	case 0: return getxattrat_compat(fd, path, flags, "user.test", value_buffer, sizeof(value_buffer));
	case 1: return setxattrat_compat(fd, path, flags, "user.test", "v", 1, requested_flags);
	case 2: return listxattrat_compat(fd, path, flags, value_buffer, sizeof(value_buffer));
	default: return removexattrat_compat(fd, path, flags, "user.test");
	}
}

int
main(void)
{
	char original[PATH_MAX], child[PATH_MAX], after[PATH_MAX];
	int fd, before, status, op, flags;
	pid_t pid;

	assert(getcwd(original, sizeof(original)) != NULL);
	assert(mkdir("child", 0700) == 0);
	fd = open("child", O_RDONLY | O_DIRECTORY);
	assert(fd >= 0);
	assert(realpath("child", child) != NULL);
	for (op = 0; op < 4; op++) {
		assert(invoke(op, fd, "leaf", 0) == 7);
		assert(method == 1 && strcmp(seen_cwd, child) == 0);
		assert(strcmp(seen_path, "leaf") == 0);
		if (op != 2)
			assert(strcmp(seen_name, "user.test") == 0);
		if (op == 0 || op == 2)
			assert(seen_size == sizeof(value_buffer));
		if (op == 1) {
			assert(seen_size == 1 && strcmp(seen_value, "v") == 0);
			assert(seen_flags == 0);
			for (flags = 1; flags <= 2; flags++) {
				/* XATTR_CREATE and XATTR_REPLACE retain their bits. */
				requested_flags = flags;
				assert(invoke(op, fd, "leaf", 0) == 7);
				assert(seen_flags == flags);
				assert(invoke(op, fd, "link", AT_SYMLINK_NOFOLLOW) == 7);
				assert(seen_flags == flags && method == 2);
				assert(invoke(op, fd, "", AT_EMPTY_PATH) == 7);
				assert(seen_flags == flags && method == 3);
			}
			requested_flags = 0;
		}
		assert(getcwd(after, sizeof(after)) != NULL);
		assert(strcmp(after, original) == 0);
		assert(invoke(op, fd, "link", AT_SYMLINK_NOFOLLOW) == 7);
		assert(method == 2 && strcmp(seen_cwd, child) == 0);
		assert(invoke(op, -1, "/absolute", 0) == 7);
		assert(method == 1 && strcmp(seen_cwd, original) == 0);
		assert(invoke(op, AT_FDCWD, "relative", 0) == 7);
		assert(method == 1 && strcmp(seen_cwd, original) == 0);
		assert(invoke(op, fd, "", AT_EMPTY_PATH) == 7);
		assert(method == 3 && seen_fd == fd);
		assert(invoke(op, AT_FDCWD, "", AT_EMPTY_PATH) == 7);
		assert(method == 1 && strcmp(seen_path, ".") == 0);
		before = calls;
		assert(invoke(op, fd, "", 0) == -1 && errno == ENOENT);
		assert(invoke(op, fd, "leaf", 0x40000000) == -1 && errno == EINVAL);
		assert(invoke(op, -1, "leaf", 0) == -1 && errno == EBADF);
		assert(calls == before);
		assert(getcwd(after, sizeof(after)) != NULL && strcmp(after, original) == 0);
		injected_error = EIO;
		assert(invoke(op, fd, "leaf", 0) == -1 && errno == EIO);
		assert(getcwd(after, sizeof(after)) != NULL && strcmp(after, original) == 0);
		injected_error = 0;
		pid = fork();
		assert(pid != -1);
		if (pid == 0) {
			chdirs = 0;
			fail_chdir = 2;
			(void)invoke(op, fd, "leaf", 0);
			_exit(99);
		}
		assert(waitpid(pid, &status, 0) == pid);
		assert(WIFEXITED(status) && WEXITSTATUS(status) == EXIT_FAILURE);
	}
	close(fd);
	assert(rmdir("child") == 0);
	puts("PASS: four xattr operations, cwd/dirfd dispatch, flags, errno and fatal restore failures");
	return 0;
}
