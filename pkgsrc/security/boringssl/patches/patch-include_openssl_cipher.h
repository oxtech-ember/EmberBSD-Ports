$NetBSD$

Origin: Electron BoringSSL commits bb96482 and dc51d5f; adapted for
current upstream by EmberBSD (AI-assisted).

diff --git include/openssl/cipher.h include/openssl/cipher.h
index 9ca8d27..ea53a44 100644
--- include/openssl/cipher.h
+++ include/openssl/cipher.h
@@ -633,34 +633,32 @@ OPENSSL_EXPORT const EVP_CIPHER *EVP_aes_192_ofb(void);
 // EVP_des_ede3_ecb is an alias for `EVP_des_ede3`. Use the former instead.
 OPENSSL_EXPORT const EVP_CIPHER *EVP_des_ede3_ecb(void);
 
-// EVP_aes_128_cfb128 is only available in decrepit.
+// EVP_aes_128_cfb128 returns AES-128 in CFB mode.
 OPENSSL_EXPORT const EVP_CIPHER *EVP_aes_128_cfb128(void);
+OPENSSL_EXPORT const EVP_CIPHER *EVP_aes_256_cfb128(void);
 
-// EVP_aes_128_cfb is an alias for `EVP_aes_128_cfb128` and is only available in
-// decrepit.
+// EVP_aes_128_cfb is an alias for `EVP_aes_128_cfb128`.
 OPENSSL_EXPORT const EVP_CIPHER *EVP_aes_128_cfb(void);
 
-// EVP_aes_192_cfb128 is only available in decrepit.
+// EVP_aes_192_cfb128 returns AES-192 in CFB mode.
 OPENSSL_EXPORT const EVP_CIPHER *EVP_aes_192_cfb128(void);
 
-// EVP_aes_192_cfb is an alias for `EVP_aes_192_cfb128` and is only available in
-// decrepit.
+// EVP_aes_192_cfb is an alias for `EVP_aes_192_cfb128`.
 OPENSSL_EXPORT const EVP_CIPHER *EVP_aes_192_cfb(void);
 
-// EVP_aes_256_cfb128 is only available in decrepit.
+// EVP_aes_256_cfb128 returns AES-256 in CFB mode.
 OPENSSL_EXPORT const EVP_CIPHER *EVP_aes_256_cfb128(void);
 
-// EVP_aes_256_cfb is an alias for `EVP_aes_256_cfb128` and is only available in
-// decrepit.
+// EVP_aes_256_cfb is an alias for `EVP_aes_256_cfb128`.
 OPENSSL_EXPORT const EVP_CIPHER *EVP_aes_256_cfb(void);
 
-// EVP_bf_ecb is Blowfish in ECB mode and is only available in decrepit.
+// EVP_bf_ecb is Blowfish in ECB mode.
 OPENSSL_EXPORT const EVP_CIPHER *EVP_bf_ecb(void);
 
-// EVP_bf_cbc is Blowfish in CBC mode and is only available in decrepit.
+// EVP_bf_cbc is Blowfish in CBC mode.
 OPENSSL_EXPORT const EVP_CIPHER *EVP_bf_cbc(void);
 
-// EVP_bf_cfb is Blowfish in 64-bit CFB mode and is only available in decrepit.
+// EVP_bf_cfb is Blowfish in 64-bit CFB mode.
 OPENSSL_EXPORT const EVP_CIPHER *EVP_bf_cfb(void);
 
 // EVP_cast5_ecb is CAST5 in ECB mode and is only available in decrepit.
