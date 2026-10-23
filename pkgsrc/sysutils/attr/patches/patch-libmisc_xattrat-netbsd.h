$NetBSD$

Use native xattr calls in the private, single-threaded CLI backend.
Retain cwd, errno and explicit errors. libattr ABI is unchanged.
Origin: EmberBSD (AI-assisted).

--- libmisc/xattrat-netbsd.h.orig
+++ libmisc/xattrat-netbsd.h
@@ -0,0 +1,64 @@
+/*
+ * SPDX-License-Identifier: LGPL-2.1-or-later
+ * Origin: EmberBSD (AI-assisted).
+ * Private helpers for the single-threaded getfattr and setfattr tools.
+ * These helpers change process cwd. They are not a general xattrat API.
+ */
+#ifndef ATTR_XATTRAT_NETBSD_H
+#define ATTR_XATTRAT_NETBSD_H
+
+#include <sys/types.h>
+#include <sys/xattr.h>
+#include <errno.h>
+#include <fcntl.h>
+#include <stdio.h>
+#include <stdlib.h>
+#include <unistd.h>
+
+static int
+attr_cwd_enter(int dirfd, const char *path, int flags, int *saved_fd)
+{
+
+	*saved_fd = -1;
+	if ((flags & ~(AT_EMPTY_PATH | AT_SYMLINK_NOFOLLOW)) != 0) {
+		errno = EINVAL;
+		return -1;
+	}
+	if (*path == '\0' && (flags & AT_EMPTY_PATH) == 0) {
+		errno = ENOENT;
+		return -1;
+	}
+	if (*path == '\0' || *path == '/' || dirfd == AT_FDCWD)
+		return 0;
+	*saved_fd = open(".", O_RDONLY | O_DIRECTORY | O_CLOEXEC);
+	if (*saved_fd == -1)
+		return -1;
+	if (fchdir(dirfd) == -1) {
+		int error = errno;
+
+		close(*saved_fd);
+		*saved_fd = -1;
+		errno = error;
+		return -1;
+	}
+	return 0;
+}
+
+static ssize_t
+attr_cwd_leave(int saved_fd, ssize_t result)
+{
+	int error = errno;
+
+	if (saved_fd != -1) {
+		if (fchdir(saved_fd) == -1) {
+			/* A later operation must never use the wrong directory. */
+			perror("attr: cannot restore working directory");
+			exit(EXIT_FAILURE);
+		}
+		close(saved_fd);
+	}
+	errno = error;
+	return result;
+}
+
+#endif /* ATTR_XATTRAT_NETBSD_H */
