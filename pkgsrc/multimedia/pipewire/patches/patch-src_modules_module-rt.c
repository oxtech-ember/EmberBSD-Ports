$NetBSD$

NetBSD: thread id via _lwp_self().

--- src/modules/module-rt.c.orig
+++ src/modules/module-rt.c
@@ -40,6 +40,9 @@
 #if defined(__GNU__)
 #include <hurd.h>
 #endif
+#if defined(__NetBSD__)
+#include <lwp.h>
+#endif
 #include <fcntl.h>
 #include <unistd.h>
 #include <pthread.h>
@@ -257,6 +260,8 @@
 	long pid;
 	thr_self(&pid);
 	return (pid_t)pid;
+#elif defined(__NetBSD__)
+	return (pid_t)_lwp_self();
 #elif defined(__GNU__)
        mach_port_t thread = hurd_thread_self();
        return (pid_t)thread;
