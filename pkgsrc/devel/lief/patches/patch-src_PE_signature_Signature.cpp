$NetBSD$

Use the public message-digest API with current Mbed TLS.

--- src/PE/signature/Signature.cpp.orig
+++ src/PE/signature/Signature.cpp
@@ -29,7 +29,7 @@
 #include "LIEF/PE/signature/SpcIndirectData.hpp"
 #include "LIEF/PE/signature/RsaInfo.hpp"
 
-#include <psa/crypto_builtin_primitives.h>
+#include <mbedtls/md.h>
 
 #include "frozen.hpp"
 #include "internal_utils.hpp"
@@ -190,7 +190,7 @@
     case ALGORITHMS::SHA_512:
     {
       std::vector<uint8_t> out(64);
-      int ret = mbedtls_sha512(buffer, size, out.data(), /* is384 */ 0);
+      int ret = mbedtls_md(mbedtls_md_info_from_type(MBEDTLS_MD_SHA512), buffer, size, out.data());
       if (ret != 0) {
         LIEF_ERR("Hashing {} bytes with SHA-512 failed (ret: {:#x})", size, ret);
         return {};
@@ -201,7 +201,7 @@
     case ALGORITHMS::SHA_384:
     {
       std::vector<uint8_t> out(64);
-      int ret = mbedtls_sha512(buffer, size, out.data(), /* is384 */ 1);
+      int ret = mbedtls_md(mbedtls_md_info_from_type(MBEDTLS_MD_SHA384), buffer, size, out.data());
       if (ret != 0) {
         LIEF_ERR("Hashing {} bytes with SHA-384 failed (ret: {:#x})", size, ret);
         return {};
@@ -213,7 +213,7 @@
     case ALGORITHMS::SHA_256:
     {
       std::vector<uint8_t> out(32);
-      int ret = mbedtls_sha256(buffer, size, out.data(), /* is224 */ 0);
+      int ret = mbedtls_md(mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), buffer, size, out.data());
       if (ret != 0) {
         LIEF_ERR("Hashing {} bytes with SHA-256 failed (ret: {:#x})", size, ret);
         return {};
@@ -224,7 +224,7 @@
     case ALGORITHMS::SHA_1:
     {
       std::vector<uint8_t> out(20);
-      int ret = mbedtls_sha1(buffer, size, out.data());
+      int ret = mbedtls_md(mbedtls_md_info_from_type(MBEDTLS_MD_SHA1), buffer, size, out.data());
       if (ret != 0) {
         LIEF_ERR("Hashing {} bytes with SHA-1 failed (ret: {:#x})", size, ret);
         return {};
@@ -235,7 +235,7 @@
     case ALGORITHMS::MD5:
     {
       std::vector<uint8_t> out(16);
-      int ret = mbedtls_md5(buffer, size, out.data());
+      int ret = mbedtls_md(mbedtls_md_info_from_type(MBEDTLS_MD_MD5), buffer, size, out.data());
       if (ret != 0) {
         LIEF_ERR("Hashing {} bytes with MD5 failed (ret: {:#x})", size, ret);
         return {};
