$NetBSD$

Add checked RGB32 framebuffer blitting for bsdfb.

--- /dev/null
+++ src/plugins/platforms/bsdfb/qbsdfbblit_p.h
@@ -0,0 +1,67 @@
+// SPDX-License-Identifier: BSD-2-Clause
+// Origin: EmberBSD contributors (AI-assisted).
+
+#pragma once
+
+#include "qbsdfblayout_p.h"
+#include <QtGui/QImage>
+#include <QtGui/QPainter>
+#include <QtGui/QRegion>
+
+namespace QBsdFb {
+
+// Copy completed logical damage into a unique, mutable native image view.
+inline bool blit(QT_PREPEND_NAMESPACE(QImage) &destination,
+                 const QT_PREPEND_NAMESPACE(QImage) &source,
+                 const Layout &layout, Rotation rotation,
+                 const QT_PREPEND_NAMESPACE(QRegion) &logicalDamage)
+{
+    using Image = QT_PREPEND_NAMESPACE(QImage);
+    using Region = QT_PREPEND_NAMESPACE(QRegion);
+    using Rectangle = QT_PREPEND_NAMESPACE(QRect);
+    using Painter = QT_PREPEND_NAMESPACE(QPainter);
+    const Size size = logicalSize(layout, rotation);
+    if (source.isNull() || destination.isNull() || !destination.isDetached()
+        || destination.width() != layout.nativeWidth
+        || destination.height() != layout.nativeHeight
+        || destination.bytesPerLine() != layout.stride
+        || source.width() != size.width || source.height() != size.height
+        || source.format() != Image::Format_RGB32
+        || (destination.format() != Image::Format_RGB32
+            && destination.format() != Image::Format_RGBX8888))
+        return false;
+
+    Region nativeDamage;
+    for (const Rectangle &rect : logicalDamage) {
+        const auto native = nativeBounds(layout, rotation,
+            {rect.x(), rect.y(), rect.width(), rect.height()});
+        if (native)
+            nativeDamage += Rectangle(native->x, native->y, native->width, native->height);
+    }
+    if (nativeDamage.isEmpty())
+        return false;
+    Painter painter(&destination);
+    if (!painter.isActive())
+        return false;
+    painter.setCompositionMode(Painter::CompositionMode_Source);
+    painter.setClipRegion(nativeDamage);
+    switch (rotation) {
+    case Rotation::R0: break;
+    case Rotation::R90:
+        painter.translate(layout.nativeWidth, 0);
+        painter.rotate(90);
+        break;
+    case Rotation::R180:
+        painter.translate(layout.nativeWidth, layout.nativeHeight);
+        painter.rotate(180);
+        break;
+    case Rotation::R270:
+        painter.translate(0, layout.nativeHeight);
+        painter.rotate(270);
+        break;
+    }
+    painter.drawImage(QT_PREPEND_NAMESPACE(QPoint)(0, 0), source);
+    return painter.end();
+}
+
+} // namespace QBsdFb
