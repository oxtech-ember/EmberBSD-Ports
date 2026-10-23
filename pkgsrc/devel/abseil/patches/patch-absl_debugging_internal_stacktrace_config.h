$NetBSD$

Use the existing generic execinfo unwinder on NetBSD. The base execinfo
library already provides backtrace and the recipe preserves its link.
Retain the upstream thread-local reentrancy and early-initialization guards.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- absl/debugging/internal/stacktrace_config.h.orig
+++ absl/debugging/internal/stacktrace_config.h
@@ -32,7 +32,7 @@
 #define ABSL_STACKTRACE_INL_HEADER \
     "absl/debugging/internal/stacktrace_win32-inl.inc"
 
-#elif defined(__APPLE__)
+#elif defined(__APPLE__) || defined(__NetBSD__)
 #ifdef ABSL_HAVE_THREAD_LOCAL
 // Thread local support required for UnwindImpl.
 #define ABSL_STACKTRACE_INL_HEADER \
