$NetBSD: patch-glib_gthread.c,v 1.2 2024/05/08 15:44:20 adam Exp $

Fix build on NetBSD.

--- glib/gthread.c.orig
+++ glib/gthread.c
@@ -1187,7 +1187,7 @@
         pcore_count > 0)
       return pcore_count;
   }
-#elif defined(_SC_NPROCESSORS_ONLN) && defined(THREADS_POSIX) && defined(HAVE_PTHREAD_GETAFFINITY_NP)
+#elif defined(_SC_NPROCESSORS_ONLN) && defined(THREADS_POSIX) && defined(HAVE_PTHREAD_GETAFFINITY_NP) && defined(CPU_ZERO)
   {
     int ncores = MIN (sysconf (_SC_NPROCESSORS_ONLN), CPU_SETSIZE);
     cpu_set_t cpu_mask;
