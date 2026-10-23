$NetBSD$

NetBSD has no kernel struct ucred; like FreeBSD use the empty
placeholder. pthread_t, CLOCK_MONOTONIC and alloca need the default
feature set and their headers before the first system include.

--- src/pipewire/private.h.orig	2026-10-13
+++ src/pipewire/private.h
@@ -7,6 +7,16 @@
 
 /** \privatesection */
 
+#ifdef __NetBSD__
+/* NetBSD needs the default feature set for pthread_t, CLOCK_MONOTONIC
+ * and alloca, through these headers. */
+#ifndef _NETBSD_SOURCE
+#define _NETBSD_SOURCE
+#endif
+#include <pthread.h>
+#include <sys/time.h> /* CLOCK_MONOTONIC */
+#include <time.h>
+#endif
 #include <sys/socket.h>
 #include <sys/types.h> /* for pthread_t */
 
@@ -24,7 +34,7 @@
 extern "C" {
 #endif
 
-#if defined(__FreeBSD__) || defined(__MidnightBSD__) || defined(__GNU__)
+#if defined(__FreeBSD__) || defined(__MidnightBSD__) || defined(__GNU__) || defined(__NetBSD__)
 struct ucred {
 };
 #endif
