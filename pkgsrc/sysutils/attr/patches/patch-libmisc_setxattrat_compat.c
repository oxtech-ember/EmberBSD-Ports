$NetBSD$

Use native xattr calls in the private, single-threaded CLI backend.
Retain cwd, errno and explicit errors. libattr ABI is unchanged.
Origin: EmberBSD (AI-assisted).

--- libmisc/setxattrat_compat.c.orig
+++ libmisc/setxattrat_compat.c
@@ -29,6 +29,31 @@
 #define DECLARATIONS_ONLY
 #include "xattrat_compat.h"
 
+#ifdef __NetBSD__
+#include "libmisc/xattrat-netbsd.h"
+
+int
+setxattrat_compat(int dirfd, const char *path, int at_flags,
+    const char *name, const void *value, size_t size, int flags)
+{
+	int saved_fd;
+	int result;
+
+	if (attr_cwd_enter(dirfd, path, at_flags, &saved_fd) == -1)
+		return -1;
+	if (*path == '\0' && dirfd != AT_FDCWD)
+		result = fsetxattr(dirfd, name, value, size, flags);
+	else {
+		if (*path == '\0')
+			path = ".";
+		if ((at_flags & AT_SYMLINK_NOFOLLOW) != 0)
+			result = lsetxattr(path, name, value, size, flags);
+		else
+			result = setxattr(path, name, value, size, flags);
+	}
+	return attr_cwd_leave(saved_fd, result);
+}
+#else
 /* Defined in getxattrat_compat.c */
 extern int slow_empty_paths;
 
@@ -106,3 +131,5 @@
 	close(fd);
 	return ret;
 }
+
+#endif /* __NetBSD__ */
