$NetBSD$

Use native xattr calls in the private, single-threaded CLI backend.
Retain cwd, errno and explicit errors. libattr ABI is unchanged.
Origin: EmberBSD (AI-assisted).

--- libmisc/listxattrat_compat.c.orig
+++ libmisc/listxattrat_compat.c
@@ -29,6 +29,31 @@
 #define DECLARATIONS_ONLY
 #include "xattrat_compat.h"
 
+#ifdef __NetBSD__
+#include "libmisc/xattrat-netbsd.h"
+
+ssize_t
+listxattrat_compat(int dirfd, const char *path, int at_flags,
+    char *list, size_t size)
+{
+	int saved_fd;
+	ssize_t result;
+
+	if (attr_cwd_enter(dirfd, path, at_flags, &saved_fd) == -1)
+		return -1;
+	if (*path == '\0' && dirfd != AT_FDCWD)
+		result = flistxattr(dirfd, list, size);
+	else {
+		if (*path == '\0')
+			path = ".";
+		if ((at_flags & AT_SYMLINK_NOFOLLOW) != 0)
+			result = llistxattr(path, list, size);
+		else
+			result = listxattr(path, list, size);
+	}
+	return attr_cwd_leave(saved_fd, result);
+}
+#else
 /* Defined in getxattrat_compat.c */
 extern int slow_empty_paths;
 
@@ -105,3 +130,5 @@
 	close(fd);
 	return ret;
 }
+
+#endif /* __NetBSD__ */
