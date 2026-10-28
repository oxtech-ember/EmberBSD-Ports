$NetBSD$

Use the public message-digest API with current Mbed TLS.

--- src/visitors/hash.cpp.orig
+++ src/visitors/hash.cpp
@@ -17,7 +17,7 @@
 #include <numeric>
 
 #include "mbedtls_wraps.h"
-#include "psa/crypto_builtin_primitives.h"
+#include "mbedtls/md.h"
 
 #include "LIEF/hash.hpp"
 
@@ -141,7 +141,10 @@
   const auto* start = reinterpret_cast<const uint8_t*>(raw);
 
   std::vector<uint8_t> sha256(32, 0u);
-  mbedtls_sha256(start, size, sha256.data(), 0);
+  const auto* info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
+  if (info == nullptr || mbedtls_md(info, start, size, sha256.data()) != 0) {
+    return 0;
+  }
 
   return std::accumulate(sha256.begin(), sha256.end(), size_t(0),
                          [](size_t v, uint8_t n) {
