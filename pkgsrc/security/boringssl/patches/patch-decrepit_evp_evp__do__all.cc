$NetBSD$

Origin: Electron BoringSSL commits bb96482 and dc51d5f; adapted for
current upstream by EmberBSD (AI-assisted).

diff --git decrepit/evp/evp_do_all.cc decrepit/evp/evp_do_all.cc
index 584b139..afbaa46 100644
--- decrepit/evp/evp_do_all.cc
+++ decrepit/evp/evp_do_all.cc
@@ -23,8 +23,10 @@ void EVP_CIPHER_do_all_sorted(void (*callback)(const EVP_CIPHER *cipher,
                                                const char *unused, void *arg),
                               void *arg) {
   callback(EVP_aes_128_cbc(), "AES-128-CBC", nullptr, arg);
+  callback(EVP_aes_128_cfb128(), "AES-128-CFB", nullptr, arg);
   callback(EVP_aes_192_cbc(), "AES-192-CBC", nullptr, arg);
   callback(EVP_aes_256_cbc(), "AES-256-CBC", nullptr, arg);
+  callback(EVP_aes_256_cfb128(), "AES-256-CFB", nullptr, arg);
   callback(EVP_aes_128_ctr(), "AES-128-CTR", nullptr, arg);
   callback(EVP_aes_192_ctr(), "AES-192-CTR", nullptr, arg);
   callback(EVP_aes_256_ctr(), "AES-256-CTR", nullptr, arg);
@@ -37,9 +39,13 @@ void EVP_CIPHER_do_all_sorted(void (*callback)(const EVP_CIPHER *cipher,
   callback(EVP_aes_128_gcm(), "AES-128-GCM", nullptr, arg);
   callback(EVP_aes_192_gcm(), "AES-192-GCM", nullptr, arg);
   callback(EVP_aes_256_gcm(), "AES-256-GCM", nullptr, arg);
+  callback(EVP_bf_cbc(), "BF-CBC", nullptr, arg);
+  callback(EVP_bf_cfb(), "BF-CFB", nullptr, arg);
+  callback(EVP_bf_ecb(), "BF-ECB", nullptr, arg);
   callback(EVP_des_cbc(), "DES-CBC", nullptr, arg);
   callback(EVP_des_ecb(), "DES-ECB", nullptr, arg);
   callback(EVP_des_ede(), "DES-EDE", nullptr, arg);
+  callback(EVP_des_ede3(), "DES-EDE3", nullptr, arg);
   callback(EVP_des_ede_cbc(), "DES-EDE-CBC", nullptr, arg);
   callback(EVP_des_ede3_cbc(), "DES-EDE3-CBC", nullptr, arg);
   callback(EVP_rc2_cbc(), "RC2-CBC", nullptr, arg);
@@ -47,8 +53,10 @@ void EVP_CIPHER_do_all_sorted(void (*callback)(const EVP_CIPHER *cipher,
 
   // OpenSSL returns everything twice, the second time in lower case.
   callback(EVP_aes_128_cbc(), "aes-128-cbc", nullptr, arg);
+  callback(EVP_aes_128_cfb128(), "aes-128-cfb", nullptr, arg);
   callback(EVP_aes_192_cbc(), "aes-192-cbc", nullptr, arg);
   callback(EVP_aes_256_cbc(), "aes-256-cbc", nullptr, arg);
+  callback(EVP_aes_256_cfb128(), "aes-256-cfb", nullptr, arg);
   callback(EVP_aes_128_ctr(), "aes-128-ctr", nullptr, arg);
   callback(EVP_aes_192_ctr(), "aes-192-ctr", nullptr, arg);
   callback(EVP_aes_256_ctr(), "aes-256-ctr", nullptr, arg);
@@ -61,9 +69,13 @@ void EVP_CIPHER_do_all_sorted(void (*callback)(const EVP_CIPHER *cipher,
   callback(EVP_aes_128_gcm(), "aes-128-gcm", nullptr, arg);
   callback(EVP_aes_192_gcm(), "aes-192-gcm", nullptr, arg);
   callback(EVP_aes_256_gcm(), "aes-256-gcm", nullptr, arg);
+  callback(EVP_bf_cbc(), "bf-cbc", nullptr, arg);
+  callback(EVP_bf_cfb(), "bf-cfb", nullptr, arg);
+  callback(EVP_bf_ecb(), "bf-ecb", nullptr, arg);
   callback(EVP_des_cbc(), "des-cbc", nullptr, arg);
   callback(EVP_des_ecb(), "des-ecb", nullptr, arg);
   callback(EVP_des_ede(), "des-ede", nullptr, arg);
+  callback(EVP_des_ede3(), "des-ede3", nullptr, arg);
   callback(EVP_des_ede_cbc(), "des-ede-cbc", nullptr, arg);
   callback(EVP_des_ede3_cbc(), "des-ede3-cbc", nullptr, arg);
   callback(EVP_rc2_cbc(), "rc2-cbc", nullptr, arg);
@@ -76,6 +88,7 @@ void EVP_MD_do_all_sorted(void (*callback)(const EVP_MD *md,
                           void *arg) {
   callback(EVP_md4(), "MD4", nullptr, arg);
   callback(EVP_md5(), "MD5", nullptr, arg);
+  callback(EVP_ripemd160(), "RIPEMD160", nullptr, arg);
   callback(EVP_sha1(), "SHA1", nullptr, arg);
   callback(EVP_sha224(), "SHA224", nullptr, arg);
   callback(EVP_sha256(), "SHA256", nullptr, arg);
@@ -85,6 +98,7 @@ void EVP_MD_do_all_sorted(void (*callback)(const EVP_MD *md,
 
   callback(EVP_md4(), "md4", nullptr, arg);
   callback(EVP_md5(), "md5", nullptr, arg);
+  callback(EVP_ripemd160(), "ripemd160", nullptr, arg);
   callback(EVP_sha1(), "sha1", nullptr, arg);
   callback(EVP_sha224(), "sha224", nullptr, arg);
   callback(EVP_sha256(), "sha256", nullptr, arg);
