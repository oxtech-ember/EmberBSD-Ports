$NetBSD$

NetBSD framebuffer integration and optional offscreen Vulkan factory.

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
@@ -24,6 +29,9 @@
     bool hasCapability(QPlatformIntegration::Capability cap) const override;
 
     QPlatformWindow *createPlatformWindow(QWindow *window) const override;
+#if defined(Q_OS_NETBSD) && defined(EMBERBSD_BSDFB_VULKAN_OFFSCREEN) && QT_CONFIG(vulkan)
+    QPlatformVulkanInstance *createPlatformVulkanInstance(QVulkanInstance *instance) const override;
+#endif
     QPlatformBackingStore *createPlatformBackingStore(QWindow *window) const override;
 
     QAbstractEventDispatcher *createEventDispatcher() const override;
