$NetBSD: patch-v8_include_v8config.h,v 1.25 2026/09/02 13:13:40 kikadf Exp $

* Part of patchset to build chromium on NetBSD
* Based on OpenBSD's chromium patches, and
  pkgsrc's qt5-qtwebengine patches

--- include/v8config.h.orig
+++ include/v8config.h
@@ -207,6 +207,9 @@
   && !defined(V8_TARGET_OS_IOS) \
   && !defined(V8_TARGET_OS_TVOS) \
   && !defined(V8_TARGET_OS_LINUX) \
+  && !defined(V8_TARGET_OS_OPENBSD) \
+  && !defined(V8_TARGET_OS_FREEBSD) \
+  && !defined(V8_TARGET_OS_NETBSD) \
   && !defined(V8_TARGET_OS_MACOS) \
   && !defined(V8_TARGET_OS_WIN) \
   && !defined(V8_TARGET_OS_CHROMEOS)
@@ -220,6 +223,9 @@
   || defined(V8_TARGET_OS_IOS) \
   || defined(V8_TARGET_OS_TVOS) \
   || defined(V8_TARGET_OS_LINUX) \
+  || defined(V8_TARGET_OS_OPENBSD) \
+  || defined(V8_TARGET_OS_FREEBSD) \
+  || defined(V8_TARGET_OS_NETBSD) \
   || defined(V8_TARGET_OS_MACOS) \
   || defined(V8_TARGET_OS_WIN) \
   || defined(V8_TARGET_OS_CHROMEOS)
@@ -247,6 +253,18 @@
 # define V8_TARGET_OS_LINUX
 #endif
 
+#ifdef V8_OS_OPENBSD
+# define V8_TARGET_OS_OPENBSD
+#endif
+
+#ifdef V8_OS_FREEBSD
+# define V8_TARGET_OS_FREEBSD
+#endif
+
+#ifdef V8_OS_NETBSD
+# define V8_TARGET_OS_NETBSD
+#endif
+
 #ifdef V8_OS_MACOS
 # define V8_TARGET_OS_MACOS
 #endif
@@ -256,6 +274,11 @@
 #endif
 
 #endif  // V8_HAVE_TARGET_OS
+
+#if defined(V8_TARGET_OS_OPENBSD) || defined(V8_TARGET_OS_FREEBSD) || \
+    defined(V8_TARGET_OS_NETBSD)
+# define V8_TARGET_OS_BSD
+#endif
 
 #if defined(V8_TARGET_OS_ANDROID)
 # define V8_TARGET_OS_STRING "android"
@@ -265,6 +288,12 @@
 # define V8_TARGET_OS_STRING "ios"
 #elif defined(V8_TARGET_OS_LINUX)
 # define V8_TARGET_OS_STRING "linux"
+#elif defined(V8_TARGET_OS_OPENBSD)
+# define V8_TARGET_OS_STRING "openbsd"
+#elif defined(V8_TARGET_OS_FREEBSD)
+# define V8_TARGET_OS_STRING "freebsd"
+#elif defined(V8_TARGET_OS_NETBSD)
+# define V8_TARGET_OS_STRING "netbsd"
 #elif defined(V8_TARGET_OS_MACOS)
 # define V8_TARGET_OS_STRING "macos"
 #elif defined(V8_TARGET_OS_WINDOWS)
@@ -401,6 +430,8 @@
 #if (defined(_M_X64) || defined(__x86_64__)            /* x64 (everywhere) */  \
      || ((defined(__AARCH64EL__) || defined(_M_ARM64)) /* arm64, but ... */    \
          && !defined(_WIN32)))                         /* not on windows */    \
+     && !defined(__OpenBSD__)                          /* not on OpenBSD */    \
+     && !defined(__NetBSD__)                           /* not on NetBSD */     \
      && !defined(COMPONENT_BUILD)                      /* no component build */\
      && __clang_major__ >= 17                          /* clang >= 17 */
 # define V8_HAS_ATTRIBUTE_PRESERVE_MOST (__has_attribute(preserve_most))
