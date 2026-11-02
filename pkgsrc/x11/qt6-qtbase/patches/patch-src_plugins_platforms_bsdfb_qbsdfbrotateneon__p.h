$NetBSD$

Add checked 32-bit rotation helpers for bsdfb.

--- /dev/null
+++ src/plugins/platforms/bsdfb/qbsdfbrotateneon_p.h
@@ -0,0 +1,152 @@
+// SPDX-License-Identifier: BSD-2-Clause
+// Origin: EmberBSD contributors (AI-assisted).
+#pragma once
+
+#include "qbsdfblayout_p.h"
+#include <QtGui/private/qmemrotate_p.h>
+
+#include <cstddef>
+#include <cstdint>
+
+#if defined(__aarch64__) && defined(__ARM_NEON)
+#include <arm_neon.h>
+
+namespace QtRotate32Neon {
+
+inline void copyRow(std::uint32_t *destination, const std::uint32_t *source,
+                    std::ptrdiff_t count)
+{
+    while (count && (reinterpret_cast<std::uintptr_t>(destination) & 15)) {
+        *destination++ = *source++;
+        --count;
+    }
+    while (count >= 4) {
+        vst1q_u32(destination, vld1q_u32(source));
+        destination += 4;
+        source += 4;
+        count -= 4;
+    }
+    while (count--) {
+        *destination++ = *source++;
+    }
+}
+
+// Qt Rotate270 maps (x,y) to (height-1-y,x), the QPA R90 mapping.
+template<bool Rotate270>
+inline bool rotate(const std::uint32_t *source, int width, int height,
+                   int sourceStrideBytes, std::uint32_t *destination,
+                   int destinationStrideBytes)
+{
+    using Offset = std::ptrdiff_t;
+    if constexpr (sizeof(Offset) < 8)
+        return false;
+    if (!source || !destination || width < 4 || height < 4
+        || sourceStrideBytes <= 0 || destinationStrideBytes <= 0
+        || sourceStrideBytes % 4 || destinationStrideBytes % 4
+        || sourceStrideBytes < Offset(width) * 4
+        || destinationStrideBytes < Offset(height) * 4
+        || (reinterpret_cast<std::uintptr_t>(source) & 3)
+        || (reinterpret_cast<std::uintptr_t>(destination) & 3))
+        return false;
+
+    const Offset w = width;
+    const Offset h = height;
+    const Offset sourceStride = sourceStrideBytes / 4;
+    const Offset destinationStride = destinationStrideBytes / 4;
+    alignas(16) std::uint32_t scratch[4][32];
+
+    for (Offset tileX = 0; tileX < w; tileX += 32) {
+        const Offset endX = tileX + 32 < w ? tileX + 32 : w;
+        for (Offset tileQ = 0; tileQ < h; tileQ += 32) {
+            const Offset count = h - tileQ < 32 ? h - tileQ : 32;
+            Offset x = tileX;
+            for (; x + 4 <= endX; x += 4) {
+                Offset q = 0;
+                for (; q + 4 <= count; q += 4) {
+                    const Offset y = Rotate270 ? h - 1 - tileQ - q : tileQ + q;
+                    const Offset step = Rotate270 ? -sourceStride : sourceStride;
+                    const std::uint32_t *row = source + y * sourceStride + x;
+                    const uint32x4_t a = vld1q_u32(row);
+                    const uint32x4_t b = vld1q_u32(row + step);
+                    const uint32x4_t c = vld1q_u32(row + 2 * step);
+                    const uint32x4_t d = vld1q_u32(row + 3 * step);
+                    const uint64x2_t ab0 = vreinterpretq_u64_u32(vtrn1q_u32(a, b));
+                    const uint64x2_t ab1 = vreinterpretq_u64_u32(vtrn2q_u32(a, b));
+                    const uint64x2_t cd0 = vreinterpretq_u64_u32(vtrn1q_u32(c, d));
+                    const uint64x2_t cd1 = vreinterpretq_u64_u32(vtrn2q_u32(c, d));
+                    vst1q_u32(scratch[0] + q, vreinterpretq_u32_u64(vtrn1q_u64(ab0, cd0)));
+                    vst1q_u32(scratch[1] + q, vreinterpretq_u32_u64(vtrn1q_u64(ab1, cd1)));
+                    vst1q_u32(scratch[2] + q, vreinterpretq_u32_u64(vtrn2q_u64(ab0, cd0)));
+                    vst1q_u32(scratch[3] + q, vreinterpretq_u32_u64(vtrn2q_u64(ab1, cd1)));
+                }
+                for (; q < count; ++q) {
+                    const Offset y = Rotate270 ? h - 1 - tileQ - q : tileQ + q;
+                    for (Offset column = 0; column < 4; ++column)
+                        scratch[column][q] = source[y * sourceStride + x + column];
+                }
+                for (Offset column = 0; column < 4; ++column) {
+                    const Offset row = Rotate270 ? x + column : w - 1 - x - column;
+                    copyRow(destination + row * destinationStride + tileQ,
+                            scratch[column], count);
+                }
+            }
+            for (; x < endX; ++x) {
+                const Offset row = Rotate270 ? x : w - 1 - x;
+                std::uint32_t *out = destination + row * destinationStride + tileQ;
+                for (Offset q = 0; q < count; ++q) {
+                    const Offset y = Rotate270 ? h - 1 - tileQ - q : tileQ + q;
+                    out[q] = source[y * sourceStride + x];
+                }
+            }
+        }
+    }
+    return true;
+}
+
+} // namespace QtRotate32Neon
+#endif
+
+namespace QBsdFb {
+
+// QPA R90 maps (x,y) to (height-1-y,x); Qt's rotate270 helper has that mapping.
+// QPA R270 maps (x,y) to (y,width-1-x); Qt's rotate90 helper has that mapping.
+inline void rotateRgb32(Rotation rotation, const std::uint32_t *source,
+                        int width, int height, int sourceStrideBytes,
+                        std::uint32_t *destination, int destinationStrideBytes)
+{
+    switch (rotation) {
+    case Rotation::R90:
+#if defined(__aarch64__) && defined(__ARM_NEON)
+        if (width >= 4 && height >= 4
+            && QtRotate32Neon::rotate<true>(source, width, height,
+                                            sourceStrideBytes, destination,
+                                            destinationStrideBytes))
+            return;
+#endif
+        QT_PREPEND_NAMESPACE(qt_memrotate270)(
+            reinterpret_cast<const QT_PREPEND_NAMESPACE(quint32) *>(source),
+            width, height, sourceStrideBytes,
+            reinterpret_cast<QT_PREPEND_NAMESPACE(quint32) *>(destination),
+            destinationStrideBytes);
+        return;
+    case Rotation::R270:
+#if defined(__aarch64__) && defined(__ARM_NEON)
+        if (width >= 4 && height >= 4
+            && QtRotate32Neon::rotate<false>(source, width, height,
+                                             sourceStrideBytes, destination,
+                                             destinationStrideBytes))
+            return;
+#endif
+        QT_PREPEND_NAMESPACE(qt_memrotate90)(
+            reinterpret_cast<const QT_PREPEND_NAMESPACE(quint32) *>(source),
+            width, height, sourceStrideBytes,
+            reinterpret_cast<QT_PREPEND_NAMESPACE(quint32) *>(destination),
+            destinationStrideBytes);
+        return;
+    case Rotation::R0:
+    case Rotation::R180:
+        return;
+    }
+}
+
+} // namespace QBsdFb
