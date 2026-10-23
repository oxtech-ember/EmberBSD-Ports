$NetBSD$

NetBSD has no MAP_LOCKED; map without the lock hint like FreeBSD.

--- src/pipewire/mem.c.orig	2026-10-13
+++ src/pipewire/mem.c
@@ -44,7 +44,7 @@
 #define HAVE_MEMFD_CREATE 1
 #endif
 
-#if defined(__FreeBSD__) || defined(__MidnightBSD__) || defined(__GNU__)
+#if defined(__FreeBSD__) || defined(__MidnightBSD__) || defined(__GNU__) || defined(__NetBSD__)
 #define MAP_LOCKED 0
 #endif
 
