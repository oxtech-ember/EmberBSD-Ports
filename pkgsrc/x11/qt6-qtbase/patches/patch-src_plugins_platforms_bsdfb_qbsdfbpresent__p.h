$NetBSD$

Add checked native-image presentation for the framebuffer backend.

--- /dev/null
+++ src/plugins/platforms/bsdfb/qbsdfbpresent_p.h
@@ -0,0 +1,26 @@
+// SPDX-License-Identifier: BSD-2-Clause
+// Origin: EmberBSD contributors (AI-assisted).
+
+#pragma once
+
+#include "qbsdfblayout_p.h"
+#include <QtGui/QImage>
+#include <cstring>
+
+namespace QBsdFb {
+
+// Copy native pixels once. The caller serializes device access and owns the mapping.
+inline bool presentImage(QImage &target, const QImage &image, Rotation rotation)
+{
+    if (rotation != Rotation::R0 || target.isNull() || image.isNull()
+        || image.size() != target.size() || image.format() != target.format()
+        || (target.format() != QImage::Format_RGB32
+            && target.format() != QImage::Format_RGBX8888))
+        return false;
+    const auto bytes = static_cast<std::size_t>(image.width()) * 4;
+    for (int y = 0; y < image.height(); ++y)
+        std::memcpy(target.scanLine(y), image.constScanLine(y), bytes);
+    return true;
+}
+
+} // namespace QBsdFb
