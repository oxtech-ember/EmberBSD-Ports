# $NetBSD$

Honor an explicit shared-library threading ABI in Darwin debug consumers.

--- include/simdjson/portability.h.orig
+++ include/simdjson/portability.h
@@ -166,6 +166,11 @@
 #define SIMDJSON_UNTARGET_REGION
 #endif
 
+// Preserve an explicitly selected shared-library ABI for consumers.
+#ifdef SIMDJSON_THREADS_ENABLED
+#define SIMDJSON_THREADS_EXPLICITLY_ENABLED
+#endif
+
 // Is threading enabled?
 #if defined(_REENTRANT) || defined(_MT)
 #ifndef SIMDJSON_THREADS_ENABLED
@@ -176,7 +181,7 @@
 // workaround for large stack sizes under -O0.
 // https://github.com/simdjson/simdjson/issues/691
 #ifdef __APPLE__
-#ifndef __OPTIMIZE__
+#if !defined(__OPTIMIZE__) && !defined(SIMDJSON_THREADS_EXPLICITLY_ENABLED)
 // Apple systems have small stack sizes in secondary threads.
 // Lack of compiler optimization may generate high stack usage.
 // Users may want to disable threads for safety, but only when
@@ -185,7 +190,7 @@
 #undef SIMDJSON_THREADS_ENABLED
 #endif
 #endif
-
+#undef SIMDJSON_THREADS_EXPLICITLY_ENABLED
 
 #if defined(__clang__)
 #define SIMDJSON_NO_SANITIZE_UNDEFINED __attribute__((no_sanitize("undefined")))
