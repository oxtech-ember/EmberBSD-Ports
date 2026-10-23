$NetBSD$

Origin: EmberBSD (AI-assisted), count actual NetBSD descriptors in tests.
Without fdescfs, /dev/fd contains static device nodes, not the process's open
descriptors. This hid real leaks and reported consumed WAYLAND_SOCKETs as leaks.
F_MAXFD bounds the scan without opening descriptors or depending on RLIMIT_NOFILE
(which can be lowered below an already-open descriptor). Keep upstream leak and
exec checks enabled and unchanged. Not submitted upstream; upstream MIT licence.

--- tests/test-helpers.c.orig
+++ tests/test-helpers.c
@@ -23,6 +23,10 @@
  * SOFTWARE.
  */
 
+#if defined(__NetBSD__) && !defined(_NETBSD_SOURCE)
+#define _NETBSD_SOURCE
+#endif
+
 #include "config.h"
 
 #include <assert.h>
@@ -88,6 +92,29 @@ count_open_fds(void)
 	/* return the current number of entries */
 	return size / sizeof(struct kinfo_file);
 }
+#elif defined(__NetBSD__)
+#include <fcntl.h>
+
+int
+count_open_fds(void)
+{
+	int max_fd, fd, count = 0;
+
+	/* /dev/fd may contain static nodes instead of a mounted fdescfs. */
+	errno = 0;
+	max_fd = fcntl(0, F_MAXFD, 0);
+	/* F_MAXFD ignores its fd argument; -1 also means an empty table. */
+	assert(max_fd >= 0 || errno == 0);
+
+	for (fd = 0; fd <= max_fd; fd++) {
+		if (fcntl(fd, F_GETFD, 0) >= 0)
+			count++;
+		else
+			assert(errno == EBADF && "fcntl F_GETFD failed.");
+	}
+
+	return count;
+}
 #else
 int
 count_open_fds(void)
