$NetBSD$

Add a first-frame coverage and presentation gate for the bsdfb platform plugin.

--- /dev/null
+++ src/plugins/platforms/bsdfb/qbsdfbframegate_p.h
@@ -0,0 +1,68 @@
+// SPDX-License-Identifier: BSD-2-Clause
+// Origin: EmberBSD contributors (AI-assisted).
+
+#pragma once
+
+#include <QtCore/QSize>
+#include <QtCore/QRect>
+#include <QtGui/QRegion>
+
+namespace QBsdFb {
+
+class FrameGate
+{
+    using Size = QT_PREPEND_NAMESPACE(QSize);
+    using Rect = QT_PREPEND_NAMESPACE(QRect);
+    using Region = QT_PREPEND_NAMESPACE(QRegion);
+    using Id = QT_PREPEND_NAMESPACE(quintptr);
+
+public:
+    explicit FrameGate(bool preserve) : m_open(!preserve), m_presented(!preserve) {}
+    bool allowsRedraw() const { return m_open; }
+    bool hasPresentedFrame() const { return m_presented; }
+
+    void framePresented()
+    {
+        if (m_open)
+            m_presented = true;
+    }
+
+    void resetForWindow(Id id, const Size &size)
+    {
+        if (m_presented)
+            return;
+        m_open = false;
+        m_window = id;
+        m_size = size;
+        m_coverage = Region();
+    }
+
+    bool addFlush(Id id, const Size &size, const Region &region)
+    {
+        if (m_presented)
+            return false;
+        if (id != m_window || size != m_size)
+            resetForWindow(id, size);
+        if (m_open)
+            return false;
+        if (id == 0 || size.width() <= 0 || size.height() <= 0)
+            return false;
+        const Region full(Rect(0, 0, size.width(), size.height()));
+        m_coverage += region.intersected(full);
+        // QRegion::contains(QRect) tests overlap, not complete rectangle coverage.
+        if (!full.subtracted(m_coverage).isEmpty())
+            return false;
+        m_open = true;
+        m_coverage = Region();
+        return true;
+    }
+
+private:
+    bool m_open;
+    bool m_presented;
+    Id m_window = 0;
+    Size m_size;
+    Region m_coverage;
+};
+
+} // namespace QBsdFb
