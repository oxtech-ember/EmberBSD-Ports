$NetBSD$

Use opaque OpenSSL contexts in the native NetBSD backend while preserving
keyed schedule state and explicit failure cleanup.
Origin: NetBSD crypto/external/bsd/heimdal with EmberBSD lifecycle corrections.

--- lib/krb5/crypto-des-common.c
+++ lib/krb5/crypto-des-common.c
@@ -66,6 +66,10 @@
     DES_cblock ivec;
     unsigned char *p = cksum->checksum.data;
 
+#ifdef HEIMDAL_OPAQUE_EVP
+    if (HEIM_EVP_SCHEDULE_CTX(ctx, ectx) == NULL)
+        return HEIM_EVP_SCHEDULE_ERROR(ctx, context);
+#endif
     krb5_generate_random_block(p, 8);
 
     m = EVP_MD_CTX_create();
@@ -78,8 +82,8 @@
     EVP_DigestFinal_ex (m, p + 8, NULL);
     EVP_MD_CTX_destroy(m);
     memset_s(&ivec, sizeof(ivec), 0, sizeof(ivec));
-    EVP_CipherInit_ex(&ctx->ectx, NULL, NULL, NULL, (void *)&ivec, -1);
-    EVP_Cipher(&ctx->ectx, p, p, 24);
+    HEIM_EVP_TRY(EVP_CipherInit_ex(HEIM_EVP_SCHEDULE_CTX(ctx, ectx), NULL, NULL, NULL, (void *)&ivec, -1));
+    HEIM_EVP_TRY(EVP_Cipher(HEIM_EVP_SCHEDULE_CTX(ctx, ectx), p, p, 24));
 
     return 0;
 }
@@ -99,13 +103,26 @@
     DES_cblock ivec;
     krb5_error_code ret = 0;
 
+#ifdef HEIMDAL_OPAQUE_EVP
+    if (HEIM_EVP_SCHEDULE_CTX(ctx, dctx) == NULL)
+        return HEIM_EVP_SCHEDULE_ERROR(ctx, context);
+#endif
     m = EVP_MD_CTX_create();
     if (m == NULL)
 	return krb5_enomem(context);
 
     memset_s(&ivec, sizeof(ivec), 0, sizeof(ivec));
-    EVP_CipherInit_ex(&ctx->dctx, NULL, NULL, NULL, (void *)&ivec, -1);
-    EVP_Cipher(&ctx->dctx, tmp, C->checksum.data, 24);
+#ifdef HEIMDAL_OPAQUE_EVP
+    if (EVP_CipherInit_ex(HEIM_EVP_SCHEDULE_CTX(ctx, dctx), NULL, NULL, NULL, (void *)&ivec, -1) <= 0 ||
+        EVP_Cipher(HEIM_EVP_SCHEDULE_CTX(ctx, dctx), tmp, C->checksum.data, 24) <= 0) {
+        EVP_MD_CTX_destroy(m);
+        memset_s(tmp, sizeof(tmp), 0, sizeof(tmp));
+        return EINVAL;
+    }
+#else
+    EVP_CipherInit_ex(HEIM_EVP_SCHEDULE_CTX(ctx, dctx), NULL, NULL, NULL, (void *)&ivec, -1);
+    EVP_Cipher(HEIM_EVP_SCHEDULE_CTX(ctx, dctx), tmp, C->checksum.data, 24);
+#endif
 
     EVP_DigestInit_ex(m, evp_md, NULL);
     EVP_DigestUpdate(m, tmp, 8); /* confounder */
