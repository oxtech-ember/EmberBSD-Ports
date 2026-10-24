$NetBSD$

Darwin: os/log.h needs the Clang-only __builtin_os_log_format.
Skip the Apple system log when the compiler lacks it, e.g. GCC.

--- Python/pylifecycle.c.orig
+++ Python/pylifecycle.c
@@ -67,6 +67,14 @@
 #    endif
 #  else
 #    define HAS_APPLE_SYSTEM_LOG 0
+#  endif
+
+// os/log.h needs the compiler's os_log format builtin, which GCC lacks.
+#  if HAS_APPLE_SYSTEM_LOG && defined(__has_builtin)
+#    if !__has_builtin(__builtin_os_log_format)
+#      undef HAS_APPLE_SYSTEM_LOG
+#      define HAS_APPLE_SYSTEM_LOG 0
+#    endif
 #  endif
 
 #  if HAS_APPLE_SYSTEM_LOG
