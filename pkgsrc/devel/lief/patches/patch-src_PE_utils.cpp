$NetBSD$

Use the public message-digest API with current Mbed TLS.

--- src/PE/utils.cpp.orig
+++ src/PE/utils.cpp
@@ -21,7 +21,7 @@
 #endif
 
 #include "logging.hpp"
-#include "psa/crypto_builtin_primitives.h"
+#include "mbedtls/md.h"
 
 #include "LIEF/PE/utils.hpp"
 #include "LIEF/PE/Binary.hpp"
@@ -257,8 +257,12 @@
 
   std::sort(import_list.begin(), import_list.end(), std::less<>());
 
-  mbedtls_md5(reinterpret_cast<const uint8_t*>(import_list.data()),
-              import_list.size(), md5_buffer.data());
+  const auto* info = mbedtls_md_info_from_type(MBEDTLS_MD_MD5);
+  if (info == nullptr ||
+      mbedtls_md(info, reinterpret_cast<const uint8_t*>(import_list.data()),
+                 import_list.size(), md5_buffer.data()) != 0) {
+    return {};
+  }
   return hex_dump(md5_buffer, "");
 }
 
