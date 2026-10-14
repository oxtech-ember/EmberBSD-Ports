$NetBSD$

Port the worker process controls to NetBSD. NetBSD has neither
prctl nor procctl. Watch the parent with a kqueue NOTE_EXIT thread
as the PR_SET_PDEATHSIG equivalent. Approximate the dumpable flag
with RLIMIT_CORE: a zero core limit keeps credentials out of dumps.
Origin: EmberBSD (AI-assisted), not submitted upstream.

--- greeter/worker/prctls.h.orig
+++ greeter/worker/prctls.h
@@ -3,7 +3,12 @@
 
 #pragma once
 
-#if !defined(Q_OS_FREEBSD)
+#if defined(Q_OS_NETBSD)
+#include <sys/event.h>
+#include <sys/resource.h>
+#include <unistd.h>
+#include <thread>
+#elif !defined(Q_OS_FREEBSD)
 #include <sys/prctl.h>
 #else
 #include <sys/procctl.h>
@@ -28,7 +33,31 @@
 
 [[nodiscard]] inline auto dieWithParent()
 {
-#if !defined(Q_OS_FREEBSD)
+#if defined(Q_OS_NETBSD)
+    // NetBSD has no parent-death signal. Watch the parent pid and deliver
+    // the kill to this process when the kernel reports its exit.
+    const pid_t parent = getppid();
+    if (parent <= 1) {
+        errno = ESRCH;
+        return _expecting(-1);
+    }
+    std::thread([parent] {
+        const int kq = kqueue();
+        if (kq < 0) {
+            return;
+        }
+        struct kevent change;
+        EV_SET(&change, parent, EVFILT_PROC, EV_ADD, NOTE_EXIT, 0, nullptr);
+        if (kevent(kq, &change, 1, nullptr, 0, nullptr) == 0) {
+            struct kevent event;
+            if (kevent(kq, nullptr, 0, &event, 1, nullptr) > 0) {
+                raise(SIGKILL);
+            }
+        }
+        close(kq);
+    }).detach();
+    return _expecting(0);
+#elif !defined(Q_OS_FREEBSD)
     return _expecting(prctl(PR_SET_PDEATHSIG, SIGKILL));
 #else
     auto sig = SIGKILL;
@@ -38,7 +67,12 @@
 
 [[nodiscard]] inline auto setDumpable(bool dumpable)
 {
-#if !defined(Q_OS_FREEBSD)
+#if defined(Q_OS_NETBSD)
+    struct rlimit limits;
+    limits.rlim_cur = dumpable ? RLIM_INFINITY : 0;
+    limits.rlim_max = dumpable ? RLIM_INFINITY : 0;
+    return _expecting(setrlimit(RLIMIT_CORE, &limits) == 0 ? 0 : -1);
+#elif !defined(Q_OS_FREEBSD)
     return _expecting(prctl(PR_SET_DUMPABLE, dumpable ? 1L : 0L));
 #else
     auto mode = dumpable ? PROC_TRACE_CTL_ENABLE : PROC_TRACE_CTL_DISABLE;
