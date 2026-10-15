$NetBSD$

Use a pthread event for NetBSD's private QMutex wait path.
Unnamed kernel semaphores consume one file descriptor each.
Qt allocates them in blocks of 16, 128, and 1024 without releasing idle blocks.
Preserve pending wakeups, deadlines, spurious-wakeup checks, and cancellation cleanup.
Stop on unexpected pthread failures instead of reporting a successful lock.

Origin: EmberBSD; AI-assisted port for Qt 6.12.0.

--- src/corelib/thread/qmutex_p.h.orig
+++ src/corelib/thread/qmutex_p.h
@@ -27,7 +27,11 @@
 #include "qplatformdefs.h" // _POSIX_VERSION
 
 #if defined(Q_OS_UNIX)
-#  include <semaphore.h>
+#  if defined(Q_OS_NETBSD)
+#    include <pthread.h>
+#  else
+#    include <semaphore.h>
+#  endif
 #endif
 
 struct timespec;
@@ -82,7 +86,11 @@
     void derefWaiters(int value) noexcept;
 
     //platform specific stuff
-#if defined(Q_OS_UNIX)
+#if defined(Q_OS_NETBSD)
+    pthread_mutex_t mutex;
+    pthread_cond_t cond;
+    unsigned int wakeups = 0;
+#elif defined(Q_OS_UNIX)
     sem_t semaphore;
 #endif
 };
