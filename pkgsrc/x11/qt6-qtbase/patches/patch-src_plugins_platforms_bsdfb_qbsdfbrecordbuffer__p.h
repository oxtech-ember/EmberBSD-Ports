$NetBSD$

Add bounded wscons record buffering for fragmented event reads.

--- /dev/null
+++ src/plugins/platforms/bsdfb/qbsdfbrecordbuffer_p.h
@@ -0,0 +1,50 @@
+// SPDX-License-Identifier: BSD-2-Clause
+// Origin: EmberBSD contributors (AI-assisted).
+
+#pragma once
+
+#include <array>
+#include <cstddef>
+#include <cstring>
+#include <type_traits>
+#include <utility>
+
+namespace QBsdFb {
+
+// Single-reader byte accumulator. A callback must not re-enter this buffer.
+template <class Record, std::size_t CapacityBytes = 32>
+class RecordBuffer
+{
+    static_assert(std::is_trivially_copyable_v<Record>, "Records must be trivially copyable");
+    static_assert(CapacityBytes >= sizeof(Record), "Buffer must hold at least one record");
+
+public:
+    char *writeData() noexcept { return m_bytes.data() + m_pending; }
+    std::size_t writableBytes() const noexcept { return CapacityBytes - m_pending; }
+    std::size_t pendingBytes() const noexcept { return m_pending; }
+
+    template <class Callback>
+    bool append(std::size_t count, Callback &&callback)
+    {
+        if (count > writableBytes())
+            return false;
+        m_pending += count;
+        std::size_t consumed = 0;
+        while (m_pending - consumed >= sizeof(Record)) {
+            Record record{};
+            std::memcpy(&record, m_bytes.data() + consumed, sizeof(record));
+            consumed += sizeof(record);
+            callback(std::as_const(record));
+        }
+        m_pending -= consumed;
+        if (consumed != 0 && m_pending != 0)
+            std::memmove(m_bytes.data(), m_bytes.data() + consumed, m_pending);
+        return true;
+    }
+
+private:
+    std::array<char, CapacityBytes> m_bytes{};
+    std::size_t m_pending = 0;
+};
+
+} // namespace QBsdFb
