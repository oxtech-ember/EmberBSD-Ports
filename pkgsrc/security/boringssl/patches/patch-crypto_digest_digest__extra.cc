$NetBSD$

Origin: Electron BoringSSL commits bb96482 and dc51d5f; adapted for
current upstream by EmberBSD (AI-assisted).

diff --git crypto/digest/digest_extra.cc crypto/digest/digest_extra.cc
index 4080076..453c94c 100644
--- crypto/digest/digest_extra.cc
+++ crypto/digest/digest_extra.cc
@@ -23,6 +23,7 @@
 #include <openssl/md5.h>
 #include <openssl/nid.h>
 #include <openssl/obj.h>
+#include <openssl/ripemd.h>
 #include <openssl/sha.h>
 #include <openssl/span.h>
 
@@ -44,6 +45,7 @@ struct nid_to_digest {
 };
 
 const nid_to_digest nid_to_digest_mapping[] = {
+    {NID_ripemd160, EVP_ripemd160, SN_ripemd160, LN_ripemd160},
     {NID_md4, EVP_md4, SN_md4, LN_md4},
     {NID_md5, EVP_md5, SN_md5, LN_md5},
     {NID_sha1, EVP_sha1, SN_sha1, LN_sha1},
@@ -282,6 +284,30 @@ const EVP_MD evp_md_blake2b256 = {
     /*ctx_size=*/sizeof(BLAKE2B_CTX),
 };
 
+void ripemd160_init(EVP_MD_CTX *ctx) {
+  BSSL_CHECK(RIPEMD160_Init(reinterpret_cast<RIPEMD160_CTX *>(ctx->md_data)));
+}
+
+void ripemd160_update(EVP_MD_CTX *ctx, const void *data, size_t count) {
+  BSSL_CHECK(RIPEMD160_Update(reinterpret_cast<RIPEMD160_CTX *>(ctx->md_data), data, count));
+}
+
+void ripemd160_final(EVP_MD_CTX *ctx, uint8_t *out) {
+  BSSL_CHECK(RIPEMD160_Final(out, reinterpret_cast<RIPEMD160_CTX *>(ctx->md_data)));
+}
+
+const EVP_MD evp_md_ripemd160 = {
+    /*type=*/NID_ripemd160,
+    /*md_size=*/RIPEMD160_DIGEST_LENGTH,
+    /*flags=*/0,
+    /*init=*/ripemd160_init,
+    /*update=*/ripemd160_update,
+    /*final=*/ripemd160_final,
+    /*squeeze=*/nullptr,
+    /*block_size=*/RIPEMD160_CBLOCK,
+    /*ctx_size=*/sizeof(RIPEMD160_CTX),
+};
+
 void md4_init(EVP_MD_CTX *ctx) {
   BSSL_CHECK(MD4_Init(reinterpret_cast<MD4_CTX *>(ctx->md_data)));
 }
@@ -372,6 +398,10 @@ const EVP_MD *EVP_blake2b256() { return &evp_md_blake2b256; }
 
 static_assert(sizeof(BLAKE2B_CTX) <= EVP_MAX_MD_DATA_SIZE);
 
+const EVP_MD *EVP_ripemd160() { return &evp_md_ripemd160; }
+
+static_assert(sizeof(RIPEMD160_CTX) <= EVP_MAX_MD_DATA_SIZE);
+
 const EVP_MD *EVP_md4() { return &evp_md_md4; }
 
 static_assert(sizeof(MD4_CTX) <= EVP_MAX_MD_DATA_SIZE);
