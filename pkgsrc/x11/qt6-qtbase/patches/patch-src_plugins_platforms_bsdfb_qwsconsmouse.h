$NetBSD$

Add the wscons mouse handler interface.

--- /dev/null
+++ src/plugins/platforms/bsdfb/qwsconsmouse.h
@@ -0,0 +1,40 @@
+// SPDX-License-Identifier: BSD-2-Clause
+// Origin: EmberBSD contributors (AI-assisted).
+
+#pragma once
+
+#include "qbsdfbpointer_p.h"
+#include "qbsdfbrecordbuffer_p.h"
+#include <QtCore/QObject>
+#include <QtCore/QString>
+#include <sys/types.h>
+#include <dev/wscons/wsconsio.h>
+#include <memory>
+
+QT_BEGIN_NAMESPACE
+
+class QSocketNotifier;
+
+class QWsconsMouse final : public QObject
+{
+public:
+    QWsconsMouse(QString path, QBsdFb::Layout layout, QBsdFb::Rotation rotation);
+    ~QWsconsMouse() override;
+    bool start();
+
+private:
+    void readEvents();
+    void stop();
+    void deliver(const QBsdFb::PointerInput::Output &event);
+
+    QString m_path;
+    QBsdFb::Layout m_layout;
+    QBsdFb::Rotation m_rotation;
+    int m_fd = -1;
+    bool m_registered = false;
+    std::unique_ptr<QSocketNotifier> m_notifier;
+    std::unique_ptr<QBsdFb::PointerInput> m_input;
+    QBsdFb::RecordBuffer<wscons_event, sizeof(wscons_event) * 32> m_records;
+};
+
+QT_END_NAMESPACE
