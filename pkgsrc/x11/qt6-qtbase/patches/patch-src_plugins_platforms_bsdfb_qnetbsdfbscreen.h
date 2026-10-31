$NetBSD$

Add the NetBSD framebuffer screen interface.

--- /dev/null
+++ src/plugins/platforms/bsdfb/qnetbsdfbscreen.h
@@ -0,0 +1,51 @@
+// SPDX-License-Identifier: BSD-2-Clause
+// Origin: EmberBSD contributors (AI-assisted).
+
+#pragma once
+
+#include "qbsdfblayout_p.h"
+#include "qbsdfbframegate_p.h"
+#include <QtFbSupport/private/qfbscreen_p.h>
+#include <QtCore/QPointer>
+#include <memory>
+
+QT_BEGIN_NAMESPACE
+
+class QPlatformBackingStore;
+class QWsconsMouse;
+
+class QNetBsdFbScreen final : public QFbScreen
+{
+public:
+    explicit QNetBsdFbScreen(const QStringList &arguments);
+    ~QNetBsdFbScreen() override;
+
+    bool initialize() override;
+    bool initializeInput();
+    QPlatformBackingStore *createBackingStore(QWindow *window);
+    void backingStoreResized(QWindow *window);
+    void backingStoreFlushed(QWindow *window, const QSize &imageSize, const QRegion &region);
+    QPixmap grabWindow(WId id, int x, int y, int width, int height) const override;
+    QRegion doRedraw() override;
+
+private:
+    void closeFramebuffer();
+
+    QString m_fbPath = QStringLiteral("/dev/ttyE0");
+    QString m_mousePath = QStringLiteral("/dev/wsmouse0");
+    bool m_argumentsValid = true;
+    int m_fd = -1;
+    int m_savedMode = -1;
+    bool m_modeChanged = false;
+    void *m_mapping = nullptr;
+    bool m_hasMapping = false;
+    QBsdFb::Layout m_layout;
+    QBsdFb::Rotation m_rotation = QBsdFb::Rotation::R0;
+    QBsdFb::FrameGate m_frameGate{false};
+    QPointer<QWindow> m_frameWindow;
+    QSize m_readyFrameSize;
+    QImage m_onscreenImage;
+    std::unique_ptr<QWsconsMouse> m_mouse;
+};
+
+QT_END_NAMESPACE
