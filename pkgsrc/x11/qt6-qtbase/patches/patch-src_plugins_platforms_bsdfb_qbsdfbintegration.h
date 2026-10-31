$NetBSD$

Add the NetBSD framebuffer integration declarations.

--- src/plugins/platforms/bsdfb/qbsdfbintegration.h
+++ src/plugins/platforms/bsdfb/qbsdfbintegration.h
@@ -11,7 +11,12 @@
 QT_BEGIN_NAMESPACE
 
 class QAbstractEventDispatcher;
+#if defined(Q_OS_NETBSD)
+class QNetBsdFbScreen;
+using QBsdFbScreen = QNetBsdFbScreen;
+#else
 class QBsdFbScreen;
+#endif
 class QFbVtHandler;
 
 class QBsdFbIntegration : public QPlatformIntegration, public QPlatformNativeInterface
