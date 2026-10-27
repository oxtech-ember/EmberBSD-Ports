$NetBSD$

Select input formats and preserve native resource forks safely.

--- a/ResourceFiles/ResourceFork.cc
+++ b/ResourceFiles/ResourceFork.cc
@@ -4,6 +4,58 @@
 #include <iostream>
 #include <map>
 #include <vector>
+#include <cstdint>
+
+bool Resources::readChecked(const std::string& bytes)
+{
+    const size_t size = bytes.size();
+    auto range = [size](size_t pos, size_t len) {
+        return pos <= size && len <= size - pos;
+    };
+    auto u16 = [&bytes](size_t p) -> uint16_t {
+        return (uint16_t(uint8_t(bytes[p])) << 8) | uint8_t(bytes[p+1]);
+    };
+    auto u32 = [&bytes](size_t p) -> uint32_t {
+        return (uint32_t(uint8_t(bytes[p])) << 24) |
+               (uint32_t(uint8_t(bytes[p+1])) << 16) |
+               (uint32_t(uint8_t(bytes[p+2])) << 8) | uint8_t(bytes[p+3]);
+    };
+    if (!range(0, 16)) return false;
+    const size_t data = u32(0), map = u32(4), dataLen = u32(8), mapLen = u32(12);
+    if (!range(data, dataLen) || !range(map, mapLen) || mapLen < 30) return false;
+    auto inMap = [map, mapLen](size_t p, size_t n) {
+        return p >= map && p - map <= mapLen && n <= mapLen - (p - map);
+    };
+    const size_t types = map + u16(map + 24), names = map + u16(map + 26);
+    if (!inMap(types, 2) || !inMap(names, 0)) return false;
+    const size_t count = (u16(types) + 1u) & 0xffffu;
+    if (!inMap(types + 2, count * 8)) return false;
+    Resources result;
+    for (size_t i = 0; i < count; ++i) {
+        const size_t type = types + 2 + i * 8;
+        const size_t refs = types + u16(type + 6), nrefs = size_t(u16(type + 4)) + 1;
+        if (!inMap(refs, nrefs * 12)) return false;
+        for (size_t j = 0; j < nrefs; ++j) {
+            const size_t ref = refs + j * 12;
+            const uint16_t noff = u16(ref + 2);
+            std::string name;
+            if (noff != 0xffff) {
+                const size_t at = names + noff;
+                if (!inMap(at, 1) || !inMap(at + 1, uint8_t(bytes[at]))) return false;
+                name = bytes.substr(at + 1, uint8_t(bytes[at]));
+            }
+            const uint32_t info = u32(ref + 4);
+            const size_t off = info & 0xffffffu;
+            if (off > dataLen || dataLen - off < 4) return false;
+            const size_t at = data + off, length = u32(at);
+            if (length > dataLen - off - 4) return false;
+            result.addResource(Resource(ResType(bytes.substr(type, 4)), int16_t(u16(ref)),
+                                        bytes.substr(at + 4, length), name, info >> 24));
+        }
+    }
+    resources.swap(result.resources);
+    return true;
+}
 
 void Resources::addResources(const Resources& res)
 {
