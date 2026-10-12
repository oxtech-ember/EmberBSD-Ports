$NetBSD$

NetBSD no longer defines HZ in <sys/param.h>. Derive it from CLK_TCK,
which <time.h> continues to provide.

--- src/timing/cl_t_current2.cc.orig	2026-10-12
+++ src/timing/cl_t_current2.cc
@@ -20,6 +20,10 @@
   #include <sys/types.h>
   #include <sys/param.h> // defines HZ, unit for times() is 1/HZ seconds
   #include <sys/times.h>
+#ifndef HZ
+  #include <time.h>
+  #define HZ CLK_TCK
+#endif
   extern "C" clock_t times (struct tms * buffer);
 #endif
 #include <cerrno>
