$NetBSD$

Use native xattr calls in the private, single-threaded CLI backend.
Retain cwd, errno and explicit errors. libattr ABI is unchanged.
Origin: EmberBSD (AI-assisted).

--- libmisc/getxattrat_compat.c.orig
+++ libmisc/getxattrat_compat.c
@@ -29,6 +29,31 @@
 #define DECLARATIONS_ONLY
 #include "xattrat_compat.h"
 
+#ifdef __NetBSD__
+#include "libmisc/xattrat-netbsd.h"
+
+ssize_t
+getxattrat_compat(int dirfd, const char *path, int at_flags,
+    const char *name, void *value, size_t size)
+{
+	int saved_fd;
+	ssize_t result;
+
+	if (attr_cwd_enter(dirfd, path, at_flags, &saved_fd) == -1)
+		return -1;
+	if (*path == '\0' && dirfd != AT_FDCWD)
+		result = fgetxattr(dirfd, name, value, size);
+	else {
+		if (*path == '\0')
+			path = ".";
+		if ((at_flags & AT_SYMLINK_NOFOLLOW) != 0)
+			result = lgetxattr(path, name, value, size);
+		else
+			result = getxattr(path, name, value, size);
+	}
+	return attr_cwd_leave(saved_fd, result);
+}
+#else
 /* Used in {set,list,remove}xattrat_compat.c */
 int slow_empty_paths;
 
@@ -106,3 +131,5 @@
 	close(fd);
 	return ret;
 }
+
+#endif /* __NetBSD__ */
