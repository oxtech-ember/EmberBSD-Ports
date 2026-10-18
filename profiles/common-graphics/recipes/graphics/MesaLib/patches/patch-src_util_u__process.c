$NetBSD$

Origin: EmberBSD; AI-assisted NetBSD executable-path portability repair.
Not submitted upstream. Keep process paths available without procfs.
KERN_PROC_PATHNAME returns a NUL-terminated path and its size including NUL.
Reject failed, truncated or malformed results before accessing the last byte.

--- src/util/u_process.c.orig
+++ src/util/u_process.c
@@ -236,6 +236,18 @@
    process_path[len - 1] = '\0';
 
    return len;
+#elif DETECT_OS_NETBSD
+   int mib[4] = { CTL_KERN, KERN_PROC_ARGS, getpid(), KERN_PROC_PATHNAME };
+   size_t path_len = len;
+
+   if (process_path == NULL || len == 0)
+      return 0;
+
+   if (sysctl(mib, ARRAY_SIZE(mib), process_path, &path_len, NULL, 0) != 0 ||
+       path_len == 0 || path_len > len || process_path[path_len - 1] != '\0')
+      return 0;
+
+   return path_len - 1;
 #elif DETECT_OS_POSIX
    ssize_t r;
 
