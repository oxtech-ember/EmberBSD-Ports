--- src/crypto/crypto_wolfssl.c
+++ src/crypto/crypto_wolfssl.c
@@ -3767,7 +3767,7 @@
 	}
 
 	wpa_printf(MSG_DEBUG,
-		   "wolfSSL: crypto_rsa_oaep_sha256_encrypt: wpabuf_len(in) %ld  wc_RsaEncryptSize(key->key) %d",
+		   "wolfSSL: crypto_rsa_oaep_sha256_encrypt: wpabuf_len(in) %zu  wc_RsaEncryptSize(key->key) %d",
 		   wpabuf_len(in), wc_RsaEncryptSize(&key->key));
 
 	err = wc_RsaPublicEncrypt_ex(wpabuf_head_u8(in), wpabuf_len(in),
@@ -3811,7 +3811,7 @@
 	}
 
 	wpa_printf(MSG_DEBUG,
-		   "wolfSSL: crypto_rsa_oaep_sha256_decrypt: wpabuf_len(in) %ld wc_RsaEncryptSize(key->key) %d",
+		   "wolfSSL: crypto_rsa_oaep_sha256_decrypt: wpabuf_len(in) %zu wc_RsaEncryptSize(key->key) %d",
 		   wpabuf_len(in), wc_RsaEncryptSize(&key->key));
 
 	err = wc_RsaPrivateDecrypt_ex(wpabuf_head_u8(in), wpabuf_len(in),
