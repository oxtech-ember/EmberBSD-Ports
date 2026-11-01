$NetBSD$

Add checked RGB32 framebuffer blitting for bsdfb.

--- /dev/null
+++ src/plugins/platforms/bsdfb/qbsdfbblit_p.h
@@ -0,0 +1,226 @@
+// SPDX-License-Identifier: BSD-2-Clause
+// Origin: EmberBSD contributors (AI-assisted).
+
+#pragma once
+
+#include "qbsdfblayout_p.h"
+#include "qbsdfbrotateneon_p.h"
+#include <QtGui/QImage>
+#include <QtGui/QPainter>
+#include <QtGui/QRegion>
+
+#include <algorithm>
+#include <cstddef>
+#include <cstdint>
+#include <limits>
+#include <vector>
+
+namespace QBsdFb {
+
+struct BlitRect {
+    int sourceX;
+    int sourceY;
+    int width;
+    int height;
+    int destinationX;
+    int destinationY;
+};
+
+inline bool validLayoutStorage(const Layout &layout) noexcept
+{
+    if (layout.nativeWidth <= 0 || layout.nativeHeight <= 0 || layout.stride <= 0
+        || layout.stride % 4 != 0 || layout.dataOffset % 4 != 0
+        || layout.dataOffset > layout.mapLength
+        || layout.mapLength > static_cast<std::size_t>(
+               std::numeric_limits<std::ptrdiff_t>::max()))
+        return false;
+
+    const auto width = static_cast<std::size_t>(layout.nativeWidth);
+    const auto height = static_cast<std::size_t>(layout.nativeHeight);
+    const auto stride = static_cast<std::size_t>(layout.stride);
+    if (width > std::numeric_limits<std::size_t>::max() / 4
+        || stride < width * 4
+        || height > std::numeric_limits<std::size_t>::max() / stride)
+        return false;
+
+    const std::size_t frameBytes = stride * height;
+    return frameBytes <= layout.mapLength - layout.dataOffset;
+}
+
+inline bool validImageStorage(const QT_PREPEND_NAMESPACE(QImage) &image,
+                              int width, int height) noexcept
+{
+    if (width <= 0 || height <= 0 || image.bytesPerLine() <= 0
+        || image.bytesPerLine() > std::numeric_limits<int>::max()
+        || image.bytesPerLine() % 4 != 0 || image.sizeInBytes() <= 0)
+        return false;
+
+    const auto rowBytes = static_cast<std::size_t>(width);
+    const auto stride = static_cast<std::size_t>(image.bytesPerLine());
+    if (rowBytes > std::numeric_limits<std::size_t>::max() / 4
+        || stride < rowBytes * 4
+        || static_cast<std::size_t>(height)
+               > std::numeric_limits<std::size_t>::max() / stride)
+        return false;
+
+    const auto imageBytes = static_cast<std::uint64_t>(image.sizeInBytes());
+    if (imageBytes > std::numeric_limits<std::size_t>::max())
+        return false;
+    return static_cast<std::size_t>(imageBytes)
+        >= stride * static_cast<std::size_t>(height);
+}
+
+inline bool memoryRangesOverlap(const unsigned char *first, std::size_t firstSize,
+                                const unsigned char *second,
+                                std::size_t secondSize) noexcept
+{
+    const auto firstBegin = reinterpret_cast<std::uintptr_t>(first);
+    const auto secondBegin = reinterpret_cast<std::uintptr_t>(second);
+    constexpr auto maxAddress = std::numeric_limits<std::uintptr_t>::max();
+    if (!first || !second || firstSize > maxAddress - firstBegin
+        || secondSize > maxAddress - secondBegin)
+        return true;
+    const auto firstEnd = firstBegin + firstSize;
+    const auto secondEnd = secondBegin + secondSize;
+    return firstBegin < secondEnd && secondBegin < firstEnd;
+}
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
+    const bool destinationMatchesLayout =
+        (layout.format == PixelFormat::Xrgb8888
+         && destination.format() == Image::Format_RGB32)
+        || (layout.format == PixelFormat::Xbgr8888
+            && destination.format() == Image::Format_RGBX8888);
+
+    if (!validLayoutStorage(layout) || !destinationMatchesLayout
+        || source.isNull() || destination.isNull()
+        || !destination.isDetached()
+        || destination.width() != layout.nativeWidth
+        || destination.height() != layout.nativeHeight
+        || destination.bytesPerLine() != layout.stride
+        || source.width() != logicalSize(layout, rotation).width
+        || source.height() != logicalSize(layout, rotation).height
+        || source.format() != Image::Format_RGB32
+        || (destination.format() != Image::Format_RGB32
+            && destination.format() != Image::Format_RGBX8888)
+        || !validImageStorage(source, source.width(), source.height())
+        || !validImageStorage(destination, layout.nativeWidth, layout.nativeHeight))
+        return false;
+
+    const auto sourceSize = logicalSize(layout, rotation);
+    Region nativeDamage;
+    std::vector<BlitRect> rects;
+    rects.reserve(static_cast<std::size_t>(logicalDamage.rectCount()));
+    for (const Rectangle &rect : logicalDamage) {
+        if (rect.width() <= 0 || rect.height() <= 0)
+            continue;
+        const auto left = std::max<std::int64_t>(0, rect.x());
+        const auto top = std::max<std::int64_t>(0, rect.y());
+        const auto right = std::min<std::int64_t>(sourceSize.width,
+            std::int64_t{rect.x()} + rect.width());
+        const auto bottom = std::min<std::int64_t>(sourceSize.height,
+            std::int64_t{rect.y()} + rect.height());
+        if (left >= right || top >= bottom)
+            continue;
+
+        const int x = static_cast<int>(left);
+        const int y = static_cast<int>(top);
+        const int width = static_cast<int>(right - left);
+        const int height = static_cast<int>(bottom - top);
+        const auto native = nativeBounds(layout, rotation, {x, y, width, height});
+        if (!native)
+            return false;
+        if ((rotation == Rotation::R90 || rotation == Rotation::R270)
+            && (native->width != height || native->height != width))
+            return false;
+        nativeDamage += Rectangle(native->x, native->y, native->width, native->height);
+        rects.push_back({x, y, width, height, native->x, native->y});
+    }
+    if (nativeDamage.isEmpty())
+        return false;
+
+    const bool quarterTurn = rotation == Rotation::R90 || rotation == Rotation::R270;
+    const auto *sourceBytes = source.constBits();
+    const auto *destinationBytes = destination.constBits();
+    const auto sourceBytesSize = static_cast<std::size_t>(source.sizeInBytes());
+    const auto destinationBytesSize = static_cast<std::size_t>(destination.sizeInBytes());
+    const bool rawRotation = quarterTurn
+        && layout.format == PixelFormat::Xrgb8888
+        && destination.format() == Image::Format_RGB32
+        && source.bytesPerLine() > 0 && source.bytesPerLine() % 4 == 0
+        && (reinterpret_cast<std::uintptr_t>(sourceBytes) & 3) == 0
+        && (reinterpret_cast<std::uintptr_t>(destinationBytes) & 3) == 0
+        && !memoryRangesOverlap(sourceBytes, sourceBytesSize,
+                                destinationBytes, destinationBytesSize);
+
+    if (rawRotation) {
+        auto *destinationData = destination.bits();
+        if (!destinationData)
+            return false;
+        const auto *sourceData = reinterpret_cast<const std::uint32_t *>(sourceBytes);
+        auto *destinationPixels = reinterpret_cast<std::uint32_t *>(destinationData);
+        const int sourceStride = static_cast<int>(source.bytesPerLine());
+        const int destinationStride = static_cast<int>(destination.bytesPerLine());
+        const auto sourceStridePixels = static_cast<std::size_t>(sourceStride / 4);
+        const auto destinationStridePixels = static_cast<std::size_t>(destinationStride / 4);
+        for (const BlitRect &rect : rects) {
+            const auto *sourceRect = sourceData
+                + static_cast<std::size_t>(rect.sourceY) * sourceStridePixels
+                + static_cast<std::size_t>(rect.sourceX);
+            auto *destinationRect = destinationPixels
+                + static_cast<std::size_t>(rect.destinationY) * destinationStridePixels
+                + static_cast<std::size_t>(rect.destinationX);
+            rotateRgb32(rotation, sourceRect, rect.width, rect.height, sourceStride,
+                        destinationRect, destinationStride);
+        }
+        return true;
+    }
+
+    Painter painter(&destination);
+    if (!painter.isActive())
+        return false;
+    const auto setSourceTransform = [&] {
+        switch (rotation) {
+        case Rotation::R0: break;
+        case Rotation::R90:
+            painter.translate(layout.nativeWidth, 0);
+            painter.rotate(90);
+            break;
+        case Rotation::R180:
+            painter.translate(layout.nativeWidth, layout.nativeHeight);
+            painter.rotate(180);
+            break;
+        case Rotation::R270:
+            painter.translate(0, layout.nativeHeight);
+            painter.rotate(270);
+            break;
+        }
+    };
+    if (nativeDamage.rectCount() == 1) {
+        painter.setCompositionMode(Painter::CompositionMode_Source);
+        painter.setClipRegion(nativeDamage);
+        setSourceTransform();
+        painter.drawImage(QT_PREPEND_NAMESPACE(QPoint)(0, 0), source);
+    } else {
+        for (const Rectangle &rect : nativeDamage) {
+            painter.save();
+            painter.setCompositionMode(Painter::CompositionMode_Source);
+            painter.setClipRect(rect);
+            setSourceTransform();
+            painter.drawImage(QT_PREPEND_NAMESPACE(QPoint)(0, 0), source);
+            painter.restore();
+        }
+    }
+    return painter.end();
+}
+
+} // namespace QBsdFb
