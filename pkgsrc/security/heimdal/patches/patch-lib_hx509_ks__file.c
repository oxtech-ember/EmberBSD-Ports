$NetBSD$

Use the opaque cipher context API for the NetBSD native OpenSSL backend;
keep the hcrypto and LibreSSL paths unchanged. Preserve failure cleanup.
Origin: NetBSD crypto/external/bsd/heimdal/dist/lib/hx509/ks_file.c;
EmberBSD error handling adaptation (AI-assisted).

--- lib/hx509/ks_file.c.orig
+++ lib/hx509/ks_file.c
@@ -112,11 +112,28 @@
     clear.length = len;
 
     {
+#if defined(__NetBSD__) && defined(EMBERBSD_BASE_HEIMDAL) && \
+    defined(HAVE_HCRYPTO_W_OPENSSL) && !defined(LIBRESSL_VERSION_NUMBER) && \
+    OPENSSL_VERSION_NUMBER >= 0x10100000L
+        EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
+        if (ctx == NULL) {
+            ret = ENOMEM;
+            goto clear;
+        }
+        if (EVP_CipherInit_ex(ctx, c, NULL, key, ivdata, 0) != 1 ||
+            EVP_Cipher(ctx, clear.data, cipher, len) <= 0) {
+            EVP_CIPHER_CTX_free(ctx);
+            ret = HX509_CRYPTO_INTERNAL_ERROR;
+            goto clear;
+        }
+        EVP_CIPHER_CTX_free(ctx);
+#else
 	EVP_CIPHER_CTX ctx;
 	EVP_CIPHER_CTX_init(&ctx);
 	EVP_CipherInit_ex(&ctx, c, NULL, key, ivdata, 0);
 	EVP_Cipher(&ctx, clear.data, cipher, len);
 	EVP_CIPHER_CTX_cleanup(&ctx);
+#endif
     }
 
     ret = _hx509_collector_private_key_add(context,
@@ -126,6 +143,11 @@
 					   &clear,
 					   NULL);
 
+#if defined(__NetBSD__) && defined(EMBERBSD_BASE_HEIMDAL) && \
+    defined(HAVE_HCRYPTO_W_OPENSSL) && !defined(LIBRESSL_VERSION_NUMBER) && \
+    OPENSSL_VERSION_NUMBER >= 0x10100000L
+clear:
+#endif
     memset_s(clear.data, clear.length, 0, clear.length);
     free(clear.data);
 out:
