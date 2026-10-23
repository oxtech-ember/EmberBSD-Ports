$NetBSD$

Use native xattr calls in the private, single-threaded CLI backend.
Retain cwd, errno and explicit errors. libattr ABI is unchanged.
Origin: EmberBSD (AI-assisted).

--- include/xattrat_compat.h.orig
+++ include/xattrat_compat.h
@@ -1,6 +1,11 @@
 #ifndef XATTRAT_COMPAT_H
 #define XATTRAT_COMPAT_H
 
+#if defined(__NetBSD__) && !defined(AT_EMPTY_PATH)
+/* Private libmisc flag. It is not passed to a kernel interface. */
+#define AT_EMPTY_PATH 0x1000
+#endif
+
 ssize_t getxattrat_compat(int dirfd, const char *path, int at_flags,
 			  const char *name, void *value, size_t size);
 
