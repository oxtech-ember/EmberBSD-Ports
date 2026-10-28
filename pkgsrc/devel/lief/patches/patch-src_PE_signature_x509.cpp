$NetBSD$

Initialize PSA, bound certificate date comparisons, and use the selected
Mbed TLS signature verifier as the authority. Handle key extraction failure.

Origin: EmberBSD, not submitted upstream.

--- src/PE/signature/x509.cpp.orig
+++ src/PE/signature/x509.cpp
@@ -39,6 +39,7 @@
 #include "LIEF/PE/signature/OIDToString.hpp"
 
 #include "mbedtls_wraps.h"
+#include "mbedtls_init.hpp"
 
 namespace {
 // Copied from mbedtls since this function is not exported
@@ -222,6 +223,7 @@
 }
 
 x509::certificates_t x509::parse(const std::vector<uint8_t>& content) {
+  mbedtls_init();
   auto ca = std::make_unique<mbedtls_x509_crt>(mbedtls_x509_crt{});
   mbedtls_x509_crt_init(ca.get());
   int ret = mbedtls_x509_crt_parse(ca.get(), content.data(), content.size());
@@ -287,14 +289,6 @@
       before[3] == after[3] && before[4] == after[4] && before[5] > after[5])
   {
     LIEF_DEBUG("{} > {}", before[5], after[5]);
-    return false;
-  }
-
-  if (before[0] == after[0] && before[1] == after[1] && before[2] == after[2] &&
-      before[3] == after[3] && before[4] == after[4] && before[5] == after[5] &&
-      before[6] > after[6])
-  {
-    LIEF_DEBUG("{} > {}", before[6], after[6]);
     return false;
   }
 
@@ -416,77 +410,15 @@
 std::unique_ptr<RsaInfo> x509::rsa_info() const {
   if (key_type() == KEY_TYPES::RSA) {
     mbedtls_rsa_context ctx_rsa;
-    mbedtls_rsa_init(&ctx_rsa);
-    rsa_from_pk(&x509_cert_->pk, &ctx_rsa);
+    if (rsa_from_pk(&x509_cert_->pk, &ctx_rsa) != 0) {
+      mbedtls_rsa_free(&ctx_rsa);
+      return nullptr;
+    }
     auto info = std::unique_ptr<RsaInfo>{new RsaInfo{&ctx_rsa}};
     mbedtls_rsa_free(&ctx_rsa);
     return info;
   }
   return nullptr;
-}
-
-std::vector<uint8_t> pkcs1_15_unpad(const std::vector<uint8_t>& input) {
-  // EB = 00 || BT || PS || 00 || D
-  if (input.size() < 10) {
-    return {};
-  }
-
-  // According to the RFC, the leading byte must be 0:
-  if (input[0] != 0x00) {
-    return {};
-  }
-  const uint8_t BT = input[1];
-  if (BT != 0 && BT != 1 && BT != 2) {
-    return {};
-  }
-
-  // We only support "1" type (signature)
-  if (BT != 1) {
-    return {};
-  }
-
-  auto padding_start = input.begin() + 2;
-  auto padding_end = std::find_if(padding_start, input.end(),
-                                  [](uint8_t x) { return x != 0xFF; });
-  if (padding_end == input.end()) {
-    return {};
-  }
-
-  auto content_start = padding_end + 1;
-  size_t content_size = input.size() - (content_start - input.begin());
-  if (content_start == input.end()) {
-    return {};
-  }
-
-  SpanStream stream(&*content_start, content_size);
-  ASN1Reader asn1r(stream);
-
-  {
-    auto res = asn1r.read_tag(MBEDTLS_ASN1_SEQUENCE | MBEDTLS_ASN1_CONSTRUCTED);
-    if (!res) {
-      return stream.content();
-    }
-  }
-
-  /* digestAlgorithm DigestAlgorithmIdentifier */ {
-    auto res = asn1r.read_alg();
-    if (!res) {
-      return stream.content();
-    }
-
-    LIEF_DEBUG("PKCS1 1.5 padding - Algo: {}", *res);
-  }
-
-  /* digest Digest */ {
-    auto res = asn1r.read_octet_string();
-    if (!res) {
-      return stream.content();
-    }
-    LIEF_DEBUG("PKCS1 1.5 padding - Digest: {}", hex_dump(*res));
-    return *res;
-  }
-
-  return stream.content();
 }
 
 bool x509::check_signature(const std::vector<uint8_t>& hash,
@@ -516,52 +448,12 @@
                               /* Signature provided */ signature.data(),
                               signature.size());
 
-  /* If the verification failed with mbedtls_pk_verify it
-   * does not necessarily mean that the signatures don't match.
-   *
-   * For RSA public-key scheme, mbedtls encodes the hash with
-   * rsa_rsassa_pkcs1_v15_encode() so that it expands the hash value with encoded
-   * data. On some samples, this encoding failed.
-   *
-   * In the approach below, we manually decrypt and unpad the output of the
-   * DEC(signature) as defined in the RFC #2313
-   */
+  // The selected Mbed TLS provider owns signature decoding and verification.
   if (ret != 0) {
-    if (mbedtls_pk_get_type(&ctx) == MBEDTLS_PK_RSA) {
-      size_t bitlen = mbedtls_pk_get_bitlen(&ctx);
-      if ((bitlen * 8) < 100 || (bitlen * 8) > 2048llu * 10) {
-        LIEF_INFO("Invalid RSA key length ({} bits)", bitlen * 8);
-        return false;
-      }
-      std::vector<uint8_t> decrypted(bitlen);
-      mbedtls_rsa_context ctx_rsa;
-      rsa_from_pk(&ctx, &ctx_rsa);
-
-      int ret_rsa_public =
-          mbedtls_rsa_public(&ctx_rsa, signature.data(), decrypted.data());
-      mbedtls_rsa_free(&ctx_rsa);
-
-      if (ret_rsa_public != 0) {
-        std::string strerr(1024, 0);
-        mbedtls_strerror(ret_rsa_public, const_cast<char*>(strerr.data()),
-                         strerr.size());
-        LIEF_INFO("RSA public key operation failed: '{}'", strerr);
-        return false;
-      }
-
-      std::vector<uint8_t> unpadded = pkcs1_15_unpad(decrypted);
-
-      if (unpadded == hash) {
-        return true;
-      }
-    }
-    if (ret != 0) {
-      std::string strerr(1024, 0);
-      mbedtls_strerror(ret, const_cast<char*>(strerr.data()), strerr.size());
-      LIEF_INFO("decrypt() failed with error: '{}'", strerr);
-      return false;
-    }
-    return true;
+    std::string strerr(1024, 0);
+    mbedtls_strerror(ret, strerr.data(), strerr.size());
+    LIEF_INFO("Signature verification failed: '{}'", strerr);
+    return false;
   }
   return true;
 }
