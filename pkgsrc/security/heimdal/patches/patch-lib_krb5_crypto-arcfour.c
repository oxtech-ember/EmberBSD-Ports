$NetBSD$

Use opaque OpenSSL contexts in the native NetBSD backend while preserving
keyed schedule state and explicit failure cleanup.
Origin: NetBSD crypto/external/bsd/heimdal with EmberBSD lifecycle corrections.

--- lib/krb5/crypto-arcfour.c
+++ lib/krb5/crypto-arcfour.c
@@ -127,7 +127,13 @@
 		   unsigned usage,
 		   void *ivec)
 {
-    EVP_CIPHER_CTX ctx;
+#ifdef HEIMDAL_OPAQUE_EVP
+    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
+    if (ctx == NULL)
+        return krb5_enomem(context);
+#else
+    EVP_CIPHER_CTX storage, *ctx = &storage;
+#endif
     struct _krb5_checksum_type *c = _krb5_find_checksum (CKSUMTYPE_RSA_MD5);
     Checksum k1_c, k2_c, k3_c, cksum;
     struct _krb5_key_data ke;
@@ -174,11 +180,25 @@
     if (ret)
 	krb5_abortx(context, "hmac failed");
 
-    EVP_CIPHER_CTX_init(&ctx);
-
-    EVP_CipherInit_ex(&ctx, EVP_rc4(), NULL, k3_c.checksum.data, NULL, 1);
-    EVP_Cipher(&ctx, cdata + 16, cdata + 16, len - 16);
-    EVP_CIPHER_CTX_cleanup(&ctx);
+#ifndef HEIMDAL_OPAQUE_EVP
+    EVP_CIPHER_CTX_init(ctx);
+#endif
+
+#ifdef HEIMDAL_OPAQUE_EVP
+    if (EVP_CipherInit_ex(ctx, EVP_rc4(), NULL, k3_c.checksum.data, NULL, 1) <= 0 ||
+        (len > 16 && EVP_Cipher(ctx, cdata + 16, cdata + 16, len - 16) <= 0)) {
+        EVP_CIPHER_CTX_free(ctx);
+        memset_s(k1_c_data, sizeof(k1_c_data), 0, sizeof(k1_c_data));
+        memset_s(k2_c_data, sizeof(k2_c_data), 0, sizeof(k2_c_data));
+        memset_s(k3_c_data, sizeof(k3_c_data), 0, sizeof(k3_c_data));
+        return EINVAL;
+    }
+    EVP_CIPHER_CTX_free(ctx);
+#else
+    EVP_CipherInit_ex(ctx, EVP_rc4(), NULL, k3_c.checksum.data, NULL, 1);
+    EVP_Cipher(ctx, cdata + 16, cdata + 16, len - 16);
+    EVP_CIPHER_CTX_cleanup(ctx);
+#endif
 
     memset_s(k1_c_data, sizeof(k1_c_data), 0, sizeof(k1_c_data));
     memset_s(k2_c_data, sizeof(k2_c_data), 0, sizeof(k2_c_data));
@@ -194,7 +214,13 @@
 		   unsigned usage,
 		   void *ivec)
 {
-    EVP_CIPHER_CTX ctx;
+#ifdef HEIMDAL_OPAQUE_EVP
+    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
+    if (ctx == NULL)
+        return krb5_enomem(context);
+#else
+    EVP_CIPHER_CTX storage, *ctx = &storage;
+#endif
     struct _krb5_checksum_type *c = _krb5_find_checksum (CKSUMTYPE_RSA_MD5);
     Checksum k1_c, k2_c, k3_c, cksum;
     struct _krb5_key_data ke;
@@ -232,10 +258,24 @@
     if (ret)
 	krb5_abortx(context, "hmac failed");
 
-    EVP_CIPHER_CTX_init(&ctx);
-    EVP_CipherInit_ex(&ctx, EVP_rc4(), NULL, k3_c.checksum.data, NULL, 0);
-    EVP_Cipher(&ctx, cdata + 16, cdata + 16, len - 16);
-    EVP_CIPHER_CTX_cleanup(&ctx);
+#ifndef HEIMDAL_OPAQUE_EVP
+    EVP_CIPHER_CTX_init(ctx);
+#endif
+#ifdef HEIMDAL_OPAQUE_EVP
+    if (EVP_CipherInit_ex(ctx, EVP_rc4(), NULL, k3_c.checksum.data, NULL, 0) <= 0 ||
+        (len > 16 && EVP_Cipher(ctx, cdata + 16, cdata + 16, len - 16) <= 0)) {
+        EVP_CIPHER_CTX_free(ctx);
+        memset_s(k1_c_data, sizeof(k1_c_data), 0, sizeof(k1_c_data));
+        memset_s(k2_c_data, sizeof(k2_c_data), 0, sizeof(k2_c_data));
+        memset_s(k3_c_data, sizeof(k3_c_data), 0, sizeof(k3_c_data));
+        return EINVAL;
+    }
+    EVP_CIPHER_CTX_free(ctx);
+#else
+    EVP_CipherInit_ex(ctx, EVP_rc4(), NULL, k3_c.checksum.data, NULL, 0);
+    EVP_Cipher(ctx, cdata + 16, cdata + 16, len - 16);
+    EVP_CIPHER_CTX_cleanup(ctx);
+#endif
 
     ke.key = &kb;
     kb.keyvalue = k2_c.checksum;
