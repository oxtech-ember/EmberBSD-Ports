$NetBSD$

Add checked framebuffer layout and rotation helpers for the bsdfb backend.

--- /dev/null
+++ src/plugins/platforms/bsdfb/qbsdfblayout_p.h
@@ -0,0 +1,139 @@
+// SPDX-License-Identifier: BSD-2-Clause
+// Origin: EmberBSD contributors (AI-assisted).
+
+#pragma once
+
+#include <algorithm>
+#include <cstddef>
+#include <cstdint>
+#include <limits>
+#include <optional>
+
+namespace QBsdFb {
+
+enum class Rotation { R0, R90, R180, R270 };
+enum class PixelFormat { Xrgb8888, Xbgr8888 };
+struct Point { int x, y; };
+struct Size { int width, height; };
+struct Rect { int x, y, width, height; };
+
+struct FrameInfo {
+    std::uint64_t fbsize = 0, offset = 0;
+    std::uint32_t width = 0, height = 0, stride = 0, bpp = 0, pixelType = 0, flags = 0;
+    std::uint32_t redOffset = 0, redSize = 0, greenOffset = 0, greenSize = 0;
+    std::uint32_t blueOffset = 0, blueSize = 0, alphaOffset = 0, alphaSize = 0;
+};
+
+struct Layout {
+    std::size_t mapLength = 0, dataOffset = 0;
+    int nativeWidth = 0, nativeHeight = 0, stride = 0;
+    PixelFormat format = PixelFormat::Xrgb8888;
+};
+
+inline bool makeLayout(const FrameInfo &info, Layout &output) noexcept
+{
+    constexpr auto maxInt = static_cast<std::uint64_t>(std::numeric_limits<int>::max());
+    constexpr auto maxMap = static_cast<std::uint64_t>(
+        std::numeric_limits<std::ptrdiff_t>::max());
+    // wsdisplay RGB pixels, with an optional RAM flag. Split mappings are unsupported.
+    if (info.pixelType != 0 || (info.flags & ~std::uint32_t{1}) != 0
+        || info.bpp != 32 || info.redSize != 8 || info.greenSize != 8
+        || info.blueSize != 8 || info.alphaSize != 0 || info.greenOffset != 8)
+        return false;
+
+    PixelFormat format;
+    if (info.redOffset == 16 && info.blueOffset == 0)
+        format = PixelFormat::Xrgb8888;
+    else if (info.redOffset == 0 && info.blueOffset == 16)
+        format = PixelFormat::Xbgr8888;
+    else
+        return false;
+
+    if (info.width == 0 || info.height == 0 || info.width > maxInt
+        || info.height > maxInt || info.stride > maxInt
+        || info.stride % 4 != 0 || info.offset % 4 != 0
+        || info.stride < std::uint64_t{info.width} * 4
+        || info.fbsize < std::uint64_t{info.stride} * info.height
+        || info.offset > maxMap || info.fbsize > maxMap - info.offset)
+        return false;
+
+    output = {static_cast<std::size_t>(info.fbsize + info.offset),
+              static_cast<std::size_t>(info.offset),
+              static_cast<int>(info.width), static_cast<int>(info.height),
+              static_cast<int>(info.stride), format};
+    return true;
+}
+
+inline Size logicalSize(const Layout &layout, Rotation rotation) noexcept
+{
+    switch (rotation) {
+    case Rotation::R0:
+    case Rotation::R180:
+        return {layout.nativeWidth, layout.nativeHeight};
+    case Rotation::R90:
+    case Rotation::R270:
+        return {layout.nativeHeight, layout.nativeWidth};
+    }
+    return {0, 0};
+}
+
+inline std::optional<Point> nativeFromLogical(const Layout &layout, Rotation rotation,
+                                               Point point) noexcept
+{
+    const Size size = logicalSize(layout, rotation);
+    if (point.x < 0 || point.y < 0 || point.x >= size.width || point.y >= size.height)
+        return {};
+    switch (rotation) {
+    case Rotation::R0: return point;
+    case Rotation::R90: return Point{layout.nativeWidth - 1 - point.y, point.x};
+    case Rotation::R180:
+        return Point{layout.nativeWidth - 1 - point.x, layout.nativeHeight - 1 - point.y};
+    case Rotation::R270: return Point{point.y, layout.nativeHeight - 1 - point.x};
+    }
+    return {};
+}
+
+inline std::optional<Point> logicalFromNative(const Layout &layout, Rotation rotation,
+                                               Point point) noexcept
+{
+    if (point.x < 0 || point.y < 0
+        || point.x >= layout.nativeWidth || point.y >= layout.nativeHeight)
+        return {};
+    switch (rotation) {
+    case Rotation::R0: return point;
+    case Rotation::R90: return Point{point.y, layout.nativeWidth - 1 - point.x};
+    case Rotation::R180:
+        return Point{layout.nativeWidth - 1 - point.x, layout.nativeHeight - 1 - point.y};
+    case Rotation::R270: return Point{layout.nativeHeight - 1 - point.y, point.x};
+    }
+    return {};
+}
+
+inline std::optional<Rect> nativeBounds(const Layout &layout, Rotation rotation,
+                                        Rect damage) noexcept
+{
+    if (damage.width <= 0 || damage.height <= 0)
+        return {};
+    const Size size = logicalSize(layout, rotation);
+    const auto left = std::max<std::int64_t>(0, damage.x);
+    const auto top = std::max<std::int64_t>(0, damage.y);
+    const auto right = std::min<std::int64_t>(size.width,
+        std::int64_t{damage.x} + damage.width);
+    const auto bottom = std::min<std::int64_t>(size.height,
+        std::int64_t{damage.y} + damage.height);
+    if (left >= right || top >= bottom)
+        return {};
+
+    const auto a = nativeFromLogical(layout, rotation,
+        {static_cast<int>(left), static_cast<int>(top)});
+    const auto b = nativeFromLogical(layout, rotation,
+        {static_cast<int>(right - 1), static_cast<int>(bottom - 1)});
+    if (!a || !b)
+        return {};
+    // Quarter turns preserve axis-aligned rectangles; opposite corners suffice.
+    return Rect{std::min(a->x, b->x), std::min(a->y, b->y),
+                std::max(a->x, b->x) - std::min(a->x, b->x) + 1,
+                std::max(a->y, b->y) - std::min(a->y, b->y) + 1};
+}
+
+} // namespace QBsdFb
