$NetBSD$

NetBSD framebuffer integration and optional offscreen Vulkan factory.

--- src/plugins/platforms/bsdfb/qbsdfbintegration.cpp
+++ src/plugins/platforms/bsdfb/qbsdfbintegration.cpp
@@ -4,7 +4,16 @@
 // Qt-Security score:significant reason:default
 
 #include "qbsdfbintegration.h"
+#if defined(Q_OS_NETBSD)
+#include "qnetbsdfbscreen.h"
+#else
 #include "qbsdfbscreen.h"
+#endif
+
+#if defined(Q_OS_NETBSD) && defined(EMBERBSD_BSDFB_VULKAN_OFFSCREEN) && QT_CONFIG(vulkan)
+#include <QtGui/private/qbasicvulkanplatforminstance_p.h>
+#include <QtGui/qvulkaninstance.h>
+#endif
 
 #include <QtGui/private/qgenericunixfontdatabase_p.h>
 #include <QtGui/private/qgenericunixeventdispatcher_p.h>
@@ -28,6 +37,28 @@
 
 using namespace Qt::StringLiterals;
 
+#if defined(Q_OS_NETBSD) && defined(EMBERBSD_BSDFB_VULKAN_OFFSCREEN) && QT_CONFIG(vulkan)
+class QBsdFbOffscreenVulkanInstance final : public QBasicPlatformVulkanInstance
+{
+public:
+    explicit QBsdFbOffscreenVulkanInstance(QVulkanInstance *instance) : m_instance(instance)
+    {
+        loadVulkanLibrary(QStringLiteral("vulkan"), 1);
+    }
+
+    void createOrAdoptInstance() override { initInstance(m_instance, {}); }
+    bool supportsPresent(VkPhysicalDevice, uint32_t, QWindow *) override { return false; }
+
+private:
+    QVulkanInstance *m_instance;
+};
+
+QPlatformVulkanInstance *QBsdFbIntegration::createPlatformVulkanInstance(QVulkanInstance *instance) const
+{
+    return new QBsdFbOffscreenVulkanInstance(instance);
+}
+#endif
+
 QBsdFbIntegration::QBsdFbIntegration(const QStringList &paramList)
 {
     m_fontDb.reset(new QGenericUnixFontDatabase);
@@ -36,22 +67,34 @@
 
 QBsdFbIntegration::~QBsdFbIntegration()
 {
-    QWindowSystemInterface::handleScreenRemoved(m_primaryScreen.take());
+    if (m_primaryScreen)
+        QWindowSystemInterface::handleScreenRemoved(m_primaryScreen.take());
 }
 
 void QBsdFbIntegration::initialize()
 {
+#if defined(Q_OS_NETBSD)
+    if (!m_primaryScreen->initialize() || !m_primaryScreen->initializeInput()) {
+        // initialize() cannot return a status. Restore devices before terminating.
+        m_primaryScreen.reset();
+        qFatal("bsdfb: Failed to initialize display and required wscons input");
+    }
+    QWindowSystemInterface::handleScreenAdded(m_primaryScreen.data());
+#else
     if (m_primaryScreen->initialize())
         QWindowSystemInterface::handleScreenAdded(m_primaryScreen.data());
     else
         qWarning("bsdfb: Failed to initialize screen");
+#endif
 
     m_inputContext.reset(QPlatformInputContextFactory::create());
     m_nativeInterface.reset(new QPlatformNativeInterface);
+#if !defined(Q_OS_NETBSD)
     m_vtHandler.reset(new QFbVtHandler);
 
     if (!qEnvironmentVariableIntValue("QT_QPA_FB_DISABLE_INPUT"))
         createInputHandlers();
+#endif
 }
 
 bool QBsdFbIntegration::hasCapability(QPlatformIntegration::Capability cap) const
@@ -70,7 +113,11 @@
 
 QPlatformBackingStore *QBsdFbIntegration::createPlatformBackingStore(QWindow *window) const
 {
+#if defined(Q_OS_NETBSD)
+    return m_primaryScreen->createBackingStore(window);
+#else
     return new QFbBackingStore(window);
+#endif
 }
 
 QPlatformWindow *QBsdFbIntegration::createPlatformWindow(QWindow *window) const
