$NetBSD$

NetBSD has no /dev/rfkill. The D-Bus binding still builds.

--- src/rfkill.cpp.orig
+++ src/rfkill.cpp
@@ -92,6 +92,7 @@
 
 void RfkillThread::doSetSoftBlocked(quint8 blocked)
 {
+#ifdef Q_OS_LINUX
     int fd = ::open("/dev/rfkill", O_WRONLY | O_CLOEXEC);
     if (fd == -1) {
         qCWarning(BLUEZQT) << "Cannot open /dev/rfkill for writing!";
@@ -110,6 +111,10 @@
         qCWarning(BLUEZQT) << "Setting Rfkill soft block failed:" << errno;
     }
     ::close(fd);
+#else
+    Q_UNUSED(blocked);
+    qCWarning(BLUEZQT) << "rfkill is not available on this platform";
+#endif
 };
 
 Rfkill::Rfkill(QObject *parent)
