$NetBSD$

Use opaque OpenSSL contexts in the native NetBSD backend while preserving
keyed schedule state and explicit failure cleanup.
Origin: NetBSD crypto/external/bsd/heimdal with EmberBSD lifecycle corrections.

--- lib/krb5/crypto-des3.c
+++ lib/krb5/crypto-des3.c
@@ -91,13 +91,33 @@
 
     {
 	const EVP_CIPHER *c = (*crypto->et->keytype->evp)();
-	EVP_CIPHER_CTX ctx;
-
-	EVP_CIPHER_CTX_init(&ctx); /* ivec all zero */
-	EVP_CipherInit_ex(&ctx, c, NULL, derived->keyvalue.data, NULL, 1);
-	EVP_Cipher(&ctx, out->data, result.checksum.data,
-		   crypto->et->prf_length);
-	EVP_CIPHER_CTX_cleanup(&ctx);
+#ifdef HEIMDAL_OPAQUE_EVP
+	EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
+	if (ctx == NULL) {
+	    krb5_data_free(out);
+	    krb5_data_free(&result.checksum);
+	    krb5_free_keyblock(context, derived);
+	    return krb5_enomem(context);
+	}
+#else
+	EVP_CIPHER_CTX storage, *ctx = &storage;
+	EVP_CIPHER_CTX_init(ctx);
+#endif
+#ifdef HEIMDAL_OPAQUE_EVP
+	if (EVP_CipherInit_ex(ctx, c, NULL, derived->keyvalue.data, NULL, 1) <= 0 ||
+	    EVP_Cipher(ctx, out->data, result.checksum.data, crypto->et->prf_length) <= 0) {
+	    EVP_CIPHER_CTX_free(ctx);
+	    krb5_data_free(out);
+	    krb5_data_free(&result.checksum);
+	    krb5_free_keyblock(context, derived);
+	    return EINVAL;
+	}
+	EVP_CIPHER_CTX_free(ctx);
+#else
+	EVP_CipherInit_ex(ctx, c, NULL, derived->keyvalue.data, NULL, 1);
+	EVP_Cipher(ctx, out->data, result.checksum.data, crypto->et->prf_length);
+	EVP_CIPHER_CTX_cleanup(ctx);
+#endif
     }
 
     krb5_data_free(&result.checksum);
