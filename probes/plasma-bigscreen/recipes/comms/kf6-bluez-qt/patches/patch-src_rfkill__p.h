$NetBSD$

Match the existing Linux-only worker implementation and ownership.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- src/rfkill_p.h.orig
+++ src/rfkill_p.h
@@ -21,6 +21,7 @@
 namespace BluezQt
 {
 
+#ifdef Q_OS_LINUX
 class RfkillThread : public QThread
 {
     Q_OBJECT
@@ -41,12 +42,15 @@
     QMutex m_mutex;
     quint8 m_pendingBlocked;
 };
+#endif
 
 struct RfkillPrivate {
     int m_readFd = -1;
     Rfkill::State m_state = Rfkill::State::Unknown;
     QHash<quint32, Rfkill::State> m_devices;
+#ifdef Q_OS_LINUX
     RfkillThread *m_thread = nullptr;
+#endif
 };
 
 } // namespace BluezQt
