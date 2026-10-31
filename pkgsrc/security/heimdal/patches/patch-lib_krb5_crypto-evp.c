$NetBSD$

Use opaque OpenSSL contexts in the native NetBSD backend while preserving
keyed schedule state and explicit failure cleanup.
Origin: NetBSD crypto/external/bsd/heimdal with EmberBSD lifecycle corrections.

--- lib/krb5/crypto-evp.c
+++ lib/krb5/crypto-evp.c
@@ -41,19 +41,39 @@
     struct _krb5_evp_schedule *key = kd->schedule->data;
     const EVP_CIPHER *c = (*kt->evp)();
 
+#ifdef HEIMDAL_OPAQUE_EVP
+    key->error = 0;
+    key->ectx = EVP_CIPHER_CTX_new();
+    key->dctx = EVP_CIPHER_CTX_new();
+    if (key->ectx == NULL || key->dctx == NULL)
+        key->error = krb5_enomem(context);
+    else if (!EVP_CipherInit_ex(key->ectx, c, NULL, kd->key->keyvalue.data, NULL, 1) ||
+        !EVP_CipherInit_ex(key->dctx, c, NULL, kd->key->keyvalue.data, NULL, 0))
+        key->error = EINVAL;
+    if (key->error != 0) {
+        EVP_CIPHER_CTX_free(key->ectx);
+        EVP_CIPHER_CTX_free(key->dctx);
+        key->ectx = key->dctx = NULL;
+    }
+#else
     EVP_CIPHER_CTX_init(&key->ectx);
     EVP_CIPHER_CTX_init(&key->dctx);
-
     EVP_CipherInit_ex(&key->ectx, c, NULL, kd->key->keyvalue.data, NULL, 1);
     EVP_CipherInit_ex(&key->dctx, c, NULL, kd->key->keyvalue.data, NULL, 0);
+#endif
 }
 
 void
 _krb5_evp_cleanup(krb5_context context, struct _krb5_key_data *kd)
 {
     struct _krb5_evp_schedule *key = kd->schedule->data;
+#ifdef HEIMDAL_OPAQUE_EVP
+    EVP_CIPHER_CTX_free(key->ectx);
+    EVP_CIPHER_CTX_free(key->dctx);
+#else
     EVP_CIPHER_CTX_cleanup(&key->ectx);
     EVP_CIPHER_CTX_cleanup(&key->dctx);
+#endif
 }
 
 krb5_error_code
@@ -67,7 +87,11 @@
 {
     struct _krb5_evp_schedule *ctx = key->schedule->data;
     EVP_CIPHER_CTX *c;
-    c = encryptp ? &ctx->ectx : &ctx->dctx;
+    c = encryptp ? HEIM_EVP_SCHEDULE_CTX(ctx, ectx) : HEIM_EVP_SCHEDULE_CTX(ctx, dctx);
+#ifdef HEIMDAL_OPAQUE_EVP
+    if (c == NULL)
+        return HEIM_EVP_SCHEDULE_ERROR(ctx, context);
+#endif
     if (ivec == NULL) {
 	/* alloca ? */
 	size_t len2 = EVP_CIPHER_CTX_iv_length(c);
@@ -75,11 +99,23 @@
 	if (loiv == NULL)
 	    return krb5_enomem(context);
 	memset(loiv, 0, len2);
+#ifdef HEIMDAL_OPAQUE_EVP
+	int init_ok = EVP_CipherInit_ex(c, NULL, NULL, NULL, loiv, -1);
+	free(loiv);
+	if (init_ok <= 0)
+	    return EINVAL;
+#else
 	EVP_CipherInit_ex(c, NULL, NULL, NULL, loiv, -1);
 	free(loiv);
+#endif
     } else
-	EVP_CipherInit_ex(c, NULL, NULL, NULL, ivec, -1);
+	HEIM_EVP_TRY(EVP_CipherInit_ex(c, NULL, NULL, NULL, ivec, -1));
+#ifdef HEIMDAL_OPAQUE_EVP
+    if (len != 0)
+        HEIM_EVP_TRY(EVP_Cipher(c, data, data, len));
+#else
     EVP_Cipher(c, data, data, len);
+#endif
     return 0;
 }
 
@@ -100,7 +136,11 @@
     EVP_CIPHER_CTX *c;
     unsigned char *p;
 
-    c = encryptp ? &ctx->ectx : &ctx->dctx;
+    c = encryptp ? HEIM_EVP_SCHEDULE_CTX(ctx, ectx) : HEIM_EVP_SCHEDULE_CTX(ctx, dctx);
+#ifdef HEIMDAL_OPAQUE_EVP
+    if (c == NULL)
+        return HEIM_EVP_SCHEDULE_ERROR(ctx, context);
+#endif
 
     blocksize = EVP_CIPHER_CTX_block_size(c);
 
@@ -109,21 +149,22 @@
 			       "message block too short");
 	return EINVAL;
     } else if (len == blocksize) {
-	EVP_CipherInit_ex(c, NULL, NULL, NULL, zero_ivec, -1);
-	EVP_Cipher(c, data, data, len);
+	HEIM_EVP_TRY(EVP_CipherInit_ex(c, NULL, NULL, NULL, zero_ivec, -1));
+	if (len != 0)
+	    HEIM_EVP_TRY(EVP_Cipher(c, data, data, len));
 	return 0;
     }
 
     if (ivec)
-	EVP_CipherInit_ex(c, NULL, NULL, NULL, ivec, -1);
+	HEIM_EVP_TRY(EVP_CipherInit_ex(c, NULL, NULL, NULL, ivec, -1));
     else
-	EVP_CipherInit_ex(c, NULL, NULL, NULL, zero_ivec, -1);
+	HEIM_EVP_TRY(EVP_CipherInit_ex(c, NULL, NULL, NULL, zero_ivec, -1));
 
     if (encryptp) {
 
 	p = data;
 	i = ((len - 1) / blocksize) * blocksize;
-	EVP_Cipher(c, p, p, i);
+	HEIM_EVP_TRY(EVP_Cipher(c, p, p, i));
 	p += i - blocksize;
 	len -= i;
 	memcpy(ivec2, p, blocksize);
@@ -133,8 +174,8 @@
 	for (; i < blocksize; i++)
 	    tmp[i] = 0 ^ ivec2[i];
 
-	EVP_CipherInit_ex(c, NULL, NULL, NULL, zero_ivec, -1);
-	EVP_Cipher(c, p, tmp, blocksize);
+	HEIM_EVP_TRY(EVP_CipherInit_ex(c, NULL, NULL, NULL, zero_ivec, -1));
+	HEIM_EVP_TRY(EVP_Cipher(c, p, tmp, blocksize));
 
 	memcpy(p + blocksize, ivec2, len);
 	if (ivec)
@@ -147,7 +188,7 @@
 	    /* remove last two blocks and round up, decrypt this with cbc, then do cts dance */
 	    i = ((((len - blocksize * 2) + blocksize - 1) / blocksize) * blocksize);
 	    memcpy(ivec2, p + i - blocksize, blocksize);
-	    EVP_Cipher(c, p, p, i);
+	    HEIM_EVP_TRY(EVP_Cipher(c, p, p, i));
 	    p += i;
 	    len -= i + blocksize;
 	} else {
@@ -159,8 +200,8 @@
 	}
 
 	memcpy(tmp, p, blocksize);
-	EVP_CipherInit_ex(c, NULL, NULL, NULL, zero_ivec, -1);
-	EVP_Cipher(c, tmp2, p, blocksize);
+	HEIM_EVP_TRY(EVP_CipherInit_ex(c, NULL, NULL, NULL, zero_ivec, -1));
+	HEIM_EVP_TRY(EVP_Cipher(c, tmp2, p, blocksize));
 
 	memcpy(tmp3, p + blocksize, len);
 	memcpy(tmp3 + len, tmp2 + len, blocksize - len); /* xor 0 */
@@ -168,8 +209,8 @@
 	for (i = 0; i < len; i++)
 	    p[i + blocksize] = tmp2[i] ^ tmp3[i];
 
-	EVP_CipherInit_ex(c, NULL, NULL, NULL, zero_ivec, -1);
-	EVP_Cipher(c, p, tmp3, blocksize);
+	HEIM_EVP_TRY(EVP_CipherInit_ex(c, NULL, NULL, NULL, zero_ivec, -1));
+	HEIM_EVP_TRY(EVP_Cipher(c, p, tmp3, blocksize));
 
 	for (i = 0; i < blocksize; i++)
 	    p[i] ^= ivec2[i];
