$NetBSD$

Keep the complete Linux worker in its existing platform branch.
Non-Linux builds retain the upstream Unknown state. This is not a native radio backend.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- src/rfkill.cpp.orig
+++ src/rfkill.cpp
@@ -50,7 +50,6 @@
     quint8 soft;
     quint8 hard;
 };
-#endif
 
 RfkillThread::RfkillThread(QObject *parent)
     : QThread(parent)
@@ -111,6 +110,7 @@
     }
     ::close(fd);
 };
+#endif
 
 Rfkill::Rfkill(QObject *parent)
     : QObject(parent)
