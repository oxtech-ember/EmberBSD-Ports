$NetBSD$

NetBSD framebuffer integration and optional offscreen Vulkan factory.

--- src/plugins/platforms/bsdfb/qbsdfbintegration.cpp
+++ src/plugins/platforms/bsdfb/qbsdfbintegration.cpp
@@ -4,7 +4,17 @@
 // Qt-Security score:significant reason:default
 
 #include "qbsdfbintegration.h"
+#if defined(Q_OS_NETBSD)
+#include "qnetbsdfbscreen.h"
+#include <QtCore/QMutex>
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
@@ -28,6 +38,71 @@
 
 using namespace Qt::StringLiterals;
 
+#if defined(Q_OS_NETBSD)
+namespace {
+QMutex presentInterfaceMutex;
+QNetBsdFbScreen *presentScreen = nullptr;
+
+bool bsdfbPresentImage(const QImage &image)
+{
+    QMutexLocker lock(&presentInterfaceMutex);
+    return presentScreen && presentScreen->presentImage(image);
+}
+
+QImage::Format bsdfbNativeImageFormat()
+{
+    QMutexLocker lock(&presentInterfaceMutex);
+    return presentScreen ? presentScreen->nativeImageFormat() : QImage::Format_Invalid;
+}
+
+class QBsdFbNativeInterface final : public QPlatformNativeInterface
+{
+public:
+    explicit QBsdFbNativeInterface(QNetBsdFbScreen *screen)
+    {
+        QMutexLocker lock(&presentInterfaceMutex);
+        presentScreen = screen;
+    }
+    ~QBsdFbNativeInterface() override
+    {
+        // Wait for a pending copy before detaching the screen for destruction.
+        QMutexLocker lock(&presentInterfaceMutex);
+        presentScreen = nullptr;
+    }
+    QFunctionPointer platformFunction(const QByteArray &name) const override
+    {
+        if (name == "bsdfbPresentImage")
+            return reinterpret_cast<QFunctionPointer>(bsdfbPresentImage);
+        if (name == "bsdfbNativeImageFormat")
+            return reinterpret_cast<QFunctionPointer>(bsdfbNativeImageFormat);
+        return QPlatformNativeInterface::platformFunction(name);
+    }
+};
+} // namespace
+#endif
+
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
@@ -36,22 +111,39 @@
 
 QBsdFbIntegration::~QBsdFbIntegration()
 {
-    QWindowSystemInterface::handleScreenRemoved(m_primaryScreen.take());
+    m_nativeInterface.reset();
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
+#if defined(Q_OS_NETBSD)
+    m_nativeInterface.reset(new QBsdFbNativeInterface(m_primaryScreen.data()));
+#else
     m_nativeInterface.reset(new QPlatformNativeInterface);
+#endif
+#if !defined(Q_OS_NETBSD)
     m_vtHandler.reset(new QFbVtHandler);
 
     if (!qEnvironmentVariableIntValue("QT_QPA_FB_DISABLE_INPUT"))
         createInputHandlers();
+#endif
 }
 
 bool QBsdFbIntegration::hasCapability(QPlatformIntegration::Capability cap) const
@@ -70,7 +162,11 @@
 
 QPlatformBackingStore *QBsdFbIntegration::createPlatformBackingStore(QWindow *window) const
 {
+#if defined(Q_OS_NETBSD)
+    return m_primaryScreen->createBackingStore(window);
+#else
     return new QFbBackingStore(window);
+#endif
 }
 
 QPlatformWindow *QBsdFbIntegration::createPlatformWindow(QWindow *window) const
