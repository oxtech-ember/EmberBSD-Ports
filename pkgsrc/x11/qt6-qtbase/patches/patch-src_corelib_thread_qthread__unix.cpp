$NetBSD: patch-src_corelib_thread_qthread__unix.cpp,v 1.1 2026/04/30 06:38:37 adam Exp $

Origin: pkgsrc; AI-assisted EmberBSD refresh for Qt 6.12.0, not submitted upstream.

Preserve the NetBSD pthread naming signature after the new VxWorks branch.

--- src/corelib/thread/qthread_unix.cpp.orig
+++ src/corelib/thread/qthread_unix.cpp
@@ -356,6 +356,8 @@
         pthread_setname_np(name);
 #  elif defined(Q_OS_OPENBSD)
         pthread_set_name_np(pthread_self(), name);
+#  elif defined(Q_OS_NETBSD)
+        pthread_setname_np(pthread_self(), name, nullptr);
 #  elif defined(Q_OS_QNX) || defined(Q_OS_BSD4)
         pthread_setname_np(pthread_self(), name);
 #  elif defined(Q_OS_VXWORKS)
