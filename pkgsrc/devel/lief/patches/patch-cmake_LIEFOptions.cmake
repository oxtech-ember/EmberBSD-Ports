$NetBSD$

Preserve the caller-selected external tcb/span include path.
Origin: EmberBSD (AI-assisted), not submitted upstream.

--- cmake/LIEFOptions.cmake.orig
+++ cmake/LIEFOptions.cmake
@@ -115,7 +115,7 @@
 # This option enables to provide an external
 # version of https://github.com/tcbrindle/span (e.g. present on the system)
 option(LIEF_OPT_EXTERNAL_SPAN OFF)
-set(LIEF_EXTERNAL_SPAN_DIR )
+set(LIEF_EXTERNAL_SPAN_DIR "" CACHE PATH "External tcb/span include directory")
 
 # This option enables to provide an external version of Frozen
 set(_LIEF_USE_FROZEN ON)
