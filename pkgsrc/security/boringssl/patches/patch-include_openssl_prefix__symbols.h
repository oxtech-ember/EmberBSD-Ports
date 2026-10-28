$NetBSD$

Origin: upstream BoringSSL prefix-symbol generator for the
Electron RIPEMD-160 API, EmberBSD (AI-assisted).

diff --git include/openssl/prefix_symbols.h include/openssl/prefix_symbols.h
index c873e87..0850901 100644
--- include/openssl/prefix_symbols.h
+++ include/openssl/prefix_symbols.h
@@ -1380,6 +1380,7 @@
 #pragma redefine_extname EVP_rc2_40_cbc BORINGSSL_ADD_USER_LABEL_AND_PREFIX(EVP_rc2_40_cbc)
 #pragma redefine_extname EVP_rc2_cbc BORINGSSL_ADD_USER_LABEL_AND_PREFIX(EVP_rc2_cbc)
 #pragma redefine_extname EVP_rc4 BORINGSSL_ADD_USER_LABEL_AND_PREFIX(EVP_rc4)
+#pragma redefine_extname EVP_ripemd160 BORINGSSL_ADD_USER_LABEL_AND_PREFIX(EVP_ripemd160)
 #pragma redefine_extname EVP_sha1 BORINGSSL_ADD_USER_LABEL_AND_PREFIX(EVP_sha1)
 #pragma redefine_extname EVP_sha224 BORINGSSL_ADD_USER_LABEL_AND_PREFIX(EVP_sha224)
 #pragma redefine_extname EVP_sha256 BORINGSSL_ADD_USER_LABEL_AND_PREFIX(EVP_sha256)
@@ -4556,6 +4557,7 @@
 #define EVP_rc2_40_cbc BORINGSSL_ADD_PREFIX(EVP_rc2_40_cbc)
 #define EVP_rc2_cbc BORINGSSL_ADD_PREFIX(EVP_rc2_cbc)
 #define EVP_rc4 BORINGSSL_ADD_PREFIX(EVP_rc4)
+#define EVP_ripemd160 BORINGSSL_ADD_PREFIX(EVP_ripemd160)
 #define EVP_sha1 BORINGSSL_ADD_PREFIX(EVP_sha1)
 #define EVP_sha224 BORINGSSL_ADD_PREFIX(EVP_sha224)
 #define EVP_sha256 BORINGSSL_ADD_PREFIX(EVP_sha256)
