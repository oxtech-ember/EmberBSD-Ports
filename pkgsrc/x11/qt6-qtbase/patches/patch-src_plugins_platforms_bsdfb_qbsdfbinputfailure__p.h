$NetBSD$

Stop wscons input and exit on asynchronous input failure.

--- /dev/null
+++ src/plugins/platforms/bsdfb/qbsdfbinputfailure_p.h
@@ -0,0 +1,20 @@
+// SPDX-License-Identifier: BSD-2-Clause
+// Origin: EmberBSD contributors (AI-assisted).
+
+#pragma once
+
+#include <QtCore/QCoreApplication>
+#include <cstdlib>
+#include <utility>
+
+namespace QBsdFb {
+
+// Called on the notifier's GUI thread. Normal destruction only runs cleanup.
+template <typename Cleanup>
+void quitAfterInputFailure(Cleanup &&cleanup)
+{
+    std::forward<Cleanup>(cleanup)();
+    QT_PREPEND_NAMESPACE(QCoreApplication)::exit(EXIT_FAILURE);
+}
+
+} // namespace QBsdFb
