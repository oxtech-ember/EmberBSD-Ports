$NetBSD$

Use a pthread event for NetBSD's private QMutex wait path.
Unnamed kernel semaphores consume one file descriptor each.
Qt allocates them in blocks of 16, 128, and 1024 without releasing idle blocks.
Preserve pending wakeups, deadlines, spurious-wakeup checks, and cancellation cleanup.
Stop on unexpected pthread failures instead of reporting a successful lock.

Origin: EmberBSD; AI-assisted port for Qt 6.12.0.

--- src/corelib/thread/qmutex_unix.cpp.orig
+++ src/corelib/thread/qmutex_unix.cpp
@@ -11,6 +11,7 @@
 #include <errno.h>
 #include <sys/time.h>
 #include <time.h>
+#include <limits>
 #include "private/qcore_unix_p.h"
 
 #if defined(Q_OS_VXWORKS) && defined(wakeup)
@@ -19,6 +20,101 @@
 
 QT_BEGIN_NAMESPACE
 
+#if defined(Q_OS_NETBSD)
+
+static void qt_mutex_check(int code, const char *operation)
+{
+    if (code != 0)
+        qFatal("QMutex: %s failed (%d)", operation, code);
+}
+
+QMutexPrivate::QMutexPrivate()
+{
+    qt_mutex_check(pthread_mutex_init(&mutex, nullptr), "pthread_mutex_init");
+    pthread_condattr_t attr;
+    int code = pthread_condattr_init(&attr);
+    if (code != 0) {
+        qt_mutex_check(pthread_mutex_destroy(&mutex), "pthread_mutex_destroy");
+        qt_mutex_check(code, "pthread_condattr_init");
+    }
+#if QT_CONFIG(pthread_condattr_setclock)
+    if (QWaitConditionClockId != CLOCK_REALTIME) {
+        code = pthread_condattr_setclock(&attr, QWaitConditionClockId);
+        if (code != 0) {
+            qt_mutex_check(pthread_condattr_destroy(&attr), "pthread_condattr_destroy");
+            qt_mutex_check(pthread_mutex_destroy(&mutex), "pthread_mutex_destroy");
+            qt_mutex_check(code, "pthread_condattr_setclock");
+        }
+    }
+#endif
+    code = pthread_cond_init(&cond, &attr);
+    const int attrCode = pthread_condattr_destroy(&attr);
+    if (code != 0) {
+        qt_mutex_check(pthread_mutex_destroy(&mutex), "pthread_mutex_destroy");
+        qt_mutex_check(code, "pthread_cond_init");
+    }
+    if (attrCode != 0) {
+        qt_mutex_check(pthread_cond_destroy(&cond), "pthread_cond_destroy");
+        qt_mutex_check(pthread_mutex_destroy(&mutex), "pthread_mutex_destroy");
+        qt_mutex_check(attrCode, "pthread_condattr_destroy");
+    }
+}
+
+QMutexPrivate::~QMutexPrivate()
+{
+    qt_mutex_check(pthread_cond_destroy(&cond), "pthread_cond_destroy");
+    qt_mutex_check(pthread_mutex_destroy(&mutex), "pthread_mutex_destroy");
+}
+
+static void qt_mutex_unlock_cleanup(void *mutex)
+{
+    qt_mutex_check(pthread_mutex_unlock(static_cast<pthread_mutex_t *>(mutex)),
+                   "pthread_mutex_unlock");
+}
+
+bool QMutexPrivate::wait(QDeadlineTimer timeout)
+{
+    int code = 0;
+    bool acquired = false;
+    qt_mutex_check(pthread_mutex_lock(&mutex), "pthread_mutex_lock");
+    pthread_cleanup_push(qt_mutex_unlock_cleanup, &mutex);
+    while (wakeups == 0) {
+        if (timeout.isForever()) {
+            code = pthread_cond_wait(&cond, &mutex);
+        } else {
+            const timespec ts = deadlineToAbstime<QWaitConditionClockId>(timeout);
+            code = pthread_cond_timedwait(&cond, &mutex, &ts);
+        }
+        if (code != 0)
+            break;
+        // A spurious wakeup must not acquire the QMutex.
+    }
+    if ((code == 0 || code == ETIMEDOUT) && wakeups != 0) {
+        // A racing wakeup owns a token even if the deadline just expired.
+        --wakeups;
+        acquired = true;
+    }
+    // A canceled waiter must also release the private pthread mutex.
+    pthread_cleanup_pop(1);
+    if (code != ETIMEDOUT)
+        qt_mutex_check(code, "pthread_cond_wait");
+    return acquired;
+}
+
+void QMutexPrivate::wakeUp() noexcept
+{
+    qt_mutex_check(pthread_mutex_lock(&mutex), "pthread_mutex_lock");
+    if (wakeups == (std::numeric_limits<unsigned int>::max)())
+        qFatal("QMutex: wakeup count overflow");
+    // Unlike QWaitCondition, preserve a signal sent before wait().
+    ++wakeups;
+    const int code = pthread_cond_signal(&cond);
+    qt_mutex_check(pthread_mutex_unlock(&mutex), "pthread_mutex_unlock");
+    qt_mutex_check(code, "pthread_cond_signal");
+}
+
+#else
+
 static void qt_report_error(int code, const char *where, const char *what)
 {
     if (code != 0)
@@ -63,4 +159,6 @@
     qt_report_error(sem_post(&semaphore), "QMutex::unlock", "sem_post");
 }
 
+#endif // Q_OS_NETBSD
+
 QT_END_NAMESPACE
