$NetBSD$

Origin: Electron BoringSSL commits bb96482 and dc51d5f; adapted for
current upstream by EmberBSD (AI-assisted).

diff --git include/openssl/digest.h include/openssl/digest.h
index 2ce0738..8369dcc 100644
--- include/openssl/digest.h
+++ include/openssl/digest.h
@@ -34,6 +34,8 @@ extern "C" {
 // The following functions return `EVP_MD` objects that implement the named hash
 // function.
 
+// EVP_ripemd160 returns the legacy RIPEMD-160 digest.
+OPENSSL_EXPORT const EVP_MD *EVP_ripemd160(void);
 OPENSSL_EXPORT const EVP_MD *EVP_md4(void);
 OPENSSL_EXPORT const EVP_MD *EVP_md5(void);
 OPENSSL_EXPORT const EVP_MD *EVP_sha1(void);
