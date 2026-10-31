$NetBSD$

Add pointer coordinate and button event handling for the bsdfb backend.

--- /dev/null
+++ src/plugins/platforms/bsdfb/qbsdfbpointer_p.h
@@ -0,0 +1,123 @@
+// SPDX-License-Identifier: BSD-2-Clause
+// Origin: EmberBSD contributors (AI-assisted).
+
+#pragma once
+
+#include "qbsdfblayout_p.h"
+#include <algorithm>
+#include <cstdint>
+
+namespace QBsdFb {
+
+class PointerInput
+{
+public:
+    enum class EventKind { AbsoluteX, AbsoluteY, ButtonDown, ButtonUp };
+    enum class Kind { Motion, Press, Release };
+    struct AxisRange { int xMin = 0, xMax = 0, yMin = 0, yMax = 0; };
+    struct Output {
+        Kind kind = Kind::Motion;
+        Point position{};
+        std::uint32_t button = 0, buttons = 0;
+    };
+
+    PointerInput(Layout layout, Rotation rotation, AxisRange axes) noexcept
+        : m_layout(layout), m_rotation(rotation), m_axes(axes)
+    {
+        const Size size = logicalSize(layout, rotation);
+        m_valid = size.width > 0 && size.height > 0
+            && axes.xMin < axes.xMax && axes.yMin < axes.yMax;
+        if (m_valid) {
+            // wscons starts its absolute axes at zero and omits unchanged reports.
+            m_x = std::clamp(0, axes.xMin, axes.xMax);
+            m_y = std::clamp(0, axes.yMin, axes.yMax);
+            updatePosition();
+            m_delivered = m_position;
+        }
+    }
+
+    bool valid() const noexcept { return m_valid; }
+
+    template <typename Callback>
+    void feed(EventKind kind, int value, Callback &&callback)
+    {
+        if (!m_valid || !m_connected)
+            return;
+        switch (kind) {
+        case EventKind::AbsoluteX:
+            m_x = std::clamp(value, m_axes.xMin, m_axes.xMax);
+            updatePosition();
+            return;
+        case EventKind::AbsoluteY:
+            m_y = std::clamp(value, m_axes.yMin, m_axes.yMax);
+            updatePosition();
+            return;
+        case EventKind::ButtonDown:
+        case EventKind::ButtonUp:
+            break;
+        default:
+            return;
+        }
+        if (value < 0 || value > 2)
+            return;
+        const std::uint32_t bit = std::uint32_t{1} << value;
+        const bool down = kind == EventKind::ButtonDown;
+        if (((m_buttons & bit) != 0) == down)
+            return;
+        // Publish all preceding axes before the button transition, even in one read.
+        drain(callback);
+        if (down)
+            m_buttons |= bit;
+        else
+            m_buttons &= ~bit;
+        callback(Output{down ? Kind::Press : Kind::Release, m_position, bit, m_buttons});
+    }
+
+    template <typename Callback>
+    void drain(Callback &&callback)
+    {
+        if (!m_valid || !m_connected
+            || (m_position.x == m_delivered.x && m_position.y == m_delivered.y))
+            return;
+        m_delivered = m_position;
+        callback(Output{Kind::Motion, m_position, 0, m_buttons});
+    }
+
+    template <typename Callback>
+    void disconnect(Callback &&callback)
+    {
+        if (!m_valid || !m_connected)
+            return;
+        drain(callback);
+        for (int button = 0; button < 3; ++button)
+            feed(EventKind::ButtonUp, button, callback);
+        m_connected = false;
+    }
+
+private:
+    static int scaled(int raw, int minimum, int maximum, int extent) noexcept
+    {
+        const auto range = std::int64_t{maximum} - minimum;
+        const auto value = std::int64_t{raw} - minimum;
+        return static_cast<int>(value * (extent - 1) / range);
+    }
+
+    void updatePosition() noexcept
+    {
+        const Point native{scaled(m_x, m_axes.xMin, m_axes.xMax, m_layout.nativeWidth),
+                           scaled(m_y, m_axes.yMin, m_axes.yMax, m_layout.nativeHeight)};
+        const auto logical = logicalFromNative(m_layout, m_rotation, native);
+        if (logical)
+            m_position = *logical;
+    }
+
+    Layout m_layout;
+    Rotation m_rotation;
+    AxisRange m_axes;
+    bool m_valid = false, m_connected = true;
+    int m_x = 0, m_y = 0;
+    Point m_position{}, m_delivered{};
+    std::uint32_t m_buttons = 0;
+};
+
+} // namespace QBsdFb
