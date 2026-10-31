$NetBSD$

Use opaque OpenSSL contexts in the native NetBSD backend while preserving
keyed schedule state and explicit failure cleanup.
Origin: NetBSD crypto/external/bsd/heimdal with EmberBSD lifecycle corrections.

--- lib/krb5/crypto-des.c
+++ lib/krb5/crypto-des.c
@@ -224,10 +224,19 @@
     struct _krb5_evp_schedule *ctx = key->schedule->data;
     EVP_CIPHER_CTX *c;
     DES_cblock ivec;
+#ifdef HEIMDAL_OPAQUE_EVP
+    if (HEIM_EVP_SCHEDULE_CTX(ctx, ectx) == NULL || HEIM_EVP_SCHEDULE_CTX(ctx, dctx) == NULL)
+        return HEIM_EVP_SCHEDULE_ERROR(ctx, context);
+#endif
     memset(&ivec, 0, sizeof(ivec));
-    c = encryptp ? &ctx->ectx : &ctx->dctx;
-    EVP_CipherInit_ex(c, NULL, NULL, NULL, (void *)&ivec, -1);
+    c = encryptp ? HEIM_EVP_SCHEDULE_CTX(ctx, ectx) : HEIM_EVP_SCHEDULE_CTX(ctx, dctx);
+    HEIM_EVP_TRY(EVP_CipherInit_ex(c, NULL, NULL, NULL, (void *)&ivec, -1));
+#ifdef HEIMDAL_OPAQUE_EVP
+    if (len != 0)
+        HEIM_EVP_TRY(EVP_Cipher(c, data, data, len));
+#else
     EVP_Cipher(c, data, data, len);
+#endif
     return 0;
 }
 
@@ -243,10 +252,19 @@
     struct _krb5_evp_schedule *ctx = key->schedule->data;
     EVP_CIPHER_CTX *c;
     DES_cblock ivec;
+#ifdef HEIMDAL_OPAQUE_EVP
+    if (HEIM_EVP_SCHEDULE_CTX(ctx, ectx) == NULL || HEIM_EVP_SCHEDULE_CTX(ctx, dctx) == NULL)
+        return HEIM_EVP_SCHEDULE_ERROR(ctx, context);
+#endif
     memcpy(&ivec, key->key->keyvalue.data, sizeof(ivec));
-    c = encryptp ? &ctx->ectx : &ctx->dctx;
-    EVP_CipherInit_ex(c, NULL, NULL, NULL, (void *)&ivec, -1);
+    c = encryptp ? HEIM_EVP_SCHEDULE_CTX(ctx, ectx) : HEIM_EVP_SCHEDULE_CTX(ctx, dctx);
+    HEIM_EVP_TRY(EVP_CipherInit_ex(c, NULL, NULL, NULL, (void *)&ivec, -1));
+#ifdef HEIMDAL_OPAQUE_EVP
+    if (len != 0)
+        HEIM_EVP_TRY(EVP_Cipher(c, data, data, len));
+#else
     EVP_Cipher(c, data, data, len);
+#endif
     return 0;
 }
 
