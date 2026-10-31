$NetBSD$

Support opaque HMAC contexts in the native backend, check provider failures,
and release partial reply output. Preserve the portable void-return API.
Origin: NetBSD crypto/external/bsd/heimdal, with EmberBSD lifecycle fixes.

--- kdc/kx509.c
+++ kdc/kx509.c
@@ -38,6 +38,18 @@
 
 #ifdef KX509
 
+#if defined(EMBERBSD_BASE_HEIMDAL) && defined(HAVE_HCRYPTO_W_OPENSSL) && \
+    defined(OPENSSL_VERSION_NUMBER) && OPENSSL_VERSION_NUMBER >= 0x10100000L && \
+    !defined(LIBRESSL_VERSION_NUMBER)
+#define HEIMDAL_OPAQUE_HMAC 1
+#define KX509_HMAC_OK(call) ((call) == 1)
+#define KX509_HMAC_FREE(ctx) HMAC_CTX_free(ctx)
+#else
+/* The portable hcrypto operations have a void return type. */
+#define KX509_HMAC_OK(call) ((void)(call), 1)
+#define KX509_HMAC_FREE(ctx) HMAC_CTX_cleanup(ctx)
+#endif
+
 /*
  *
  */
@@ -64,7 +76,12 @@
 		krb5_keyblock *key)
 {
     unsigned char digest[SHA_DIGEST_LENGTH];
-    HMAC_CTX ctx;
+#ifdef HEIMDAL_OPAQUE_HMAC
+    HMAC_CTX *ctx;
+#else
+    HMAC_CTX storage, *ctx = &storage;
+#endif
+    int equal;
 
     if (req->pk_hash.length != sizeof(digest)) {
 	krb5_set_error_message(context, KRB5KDC_ERR_PREAUTH_FAILED,
@@ -73,23 +90,43 @@
 	return KRB5KDC_ERR_PREAUTH_FAILED;
     }
 
-    HMAC_CTX_init(&ctx);
-    HMAC_Init_ex(&ctx,
-		 key->keyvalue.data, key->keyvalue.length,
-		 EVP_sha1(), NULL);
-    if (sizeof(digest) != HMAC_size(&ctx))
+#ifdef HEIMDAL_OPAQUE_HMAC
+    ctx = HMAC_CTX_new();
+    if (ctx == NULL)
+	return krb5_enomem(context);
+#else
+    HMAC_CTX_init(ctx);
+#endif
+    if (!KX509_HMAC_OK(HMAC_Init_ex(ctx, key->keyvalue.data,
+	key->keyvalue.length, EVP_sha1(), NULL)))
+	goto crypto_error;
+    if (sizeof(digest) != HMAC_size(ctx)) {
+#ifdef HEIMDAL_OPAQUE_HMAC
+	goto crypto_error;
+#else
 	krb5_abortx(context, "runtime error, hmac buffer wrong size in kx509");
-    HMAC_Update(&ctx, version_2_0, sizeof(version_2_0));
-    HMAC_Update(&ctx, req->pk_key.data, req->pk_key.length);
-    HMAC_Final(&ctx, digest, 0);
-    HMAC_CTX_cleanup(&ctx);
-
-    if (memcmp(req->pk_hash.data, digest, sizeof(digest)) != 0) {
+#endif
+    }
+    if (!KX509_HMAC_OK(HMAC_Update(ctx, version_2_0, sizeof(version_2_0))) ||
+	!KX509_HMAC_OK(HMAC_Update(ctx, req->pk_key.data, req->pk_key.length)) ||
+	!KX509_HMAC_OK(HMAC_Final(ctx, digest, NULL)))
+	goto crypto_error;
+    KX509_HMAC_FREE(ctx);
+
+    equal = memcmp(req->pk_hash.data, digest, sizeof(digest)) == 0;
+    memset_s(digest, sizeof(digest), 0, sizeof(digest));
+    if (!equal) {
 	krb5_set_error_message(context, KRB5KDC_ERR_PREAUTH_FAILED,
 			       "pk-hash is not correct");
 	return KRB5KDC_ERR_PREAUTH_FAILED;
     }
     return 0;
+
+crypto_error:
+    memset_s(digest, sizeof(digest), 0, sizeof(digest));
+    KX509_HMAC_FREE(ctx);
+    krb5_set_error_message(context, EINVAL, "KX509 request HMAC failed");
+    return EINVAL;
 }
 
 static krb5_error_code
@@ -97,38 +134,67 @@
 		     krb5_keyblock *key,
 		     Kx509Response *rep)
 {
-    krb5_error_code ret;
-    HMAC_CTX ctx;
-
-    HMAC_CTX_init(&ctx);
-
-    HMAC_Init_ex(&ctx, key->keyvalue.data, key->keyvalue.length,
-		 EVP_sha1(), NULL);
-    ret = krb5_data_alloc(rep->hash, HMAC_size(&ctx));
+    krb5_error_code ret = EINVAL;
+#ifdef HEIMDAL_OPAQUE_HMAC
+    HMAC_CTX *ctx;
+#else
+    HMAC_CTX storage, *ctx = &storage;
+#endif
+    int allocated = 0;
+
+#ifdef HEIMDAL_OPAQUE_HMAC
+    ctx = HMAC_CTX_new();
+    if (ctx == NULL)
+	return krb5_enomem(context);
+#else
+    HMAC_CTX_init(ctx);
+#endif
+    if (!KX509_HMAC_OK(HMAC_Init_ex(ctx, key->keyvalue.data,
+	key->keyvalue.length, EVP_sha1(), NULL)))
+	goto out;
+#ifdef HEIMDAL_OPAQUE_HMAC
+    if (HMAC_size(ctx) != SHA_DIGEST_LENGTH)
+	goto out;
+#endif
+    ret = krb5_data_alloc(rep->hash, HMAC_size(ctx));
     if (ret) {
-	HMAC_CTX_cleanup(&ctx);
 	krb5_set_error_message(context, ENOMEM, "malloc: out of memory");
-	return ENOMEM;
-    }
-
-    HMAC_Update(&ctx, version_2_0, sizeof(version_2_0));
+	ret = ENOMEM;
+	goto out;
+    }
+    allocated = 1;
+    ret = EINVAL;
+
+    if (!KX509_HMAC_OK(HMAC_Update(ctx, version_2_0, sizeof(version_2_0))))
+	goto out;
     if (rep->error_code) {
 	int32_t t = *rep->error_code;
 	do {
 	    unsigned char p = (t & 0xff);
-	    HMAC_Update(&ctx, &p, 1);
+	    if (!KX509_HMAC_OK(HMAC_Update(ctx, &p, 1)))
+		goto out;
 	    t >>= 8;
 	} while (t);
     }
-    if (rep->certificate)
-	HMAC_Update(&ctx, rep->certificate->data, rep->certificate->length);
-    if (rep->e_text)
-	HMAC_Update(&ctx, (unsigned char *)*rep->e_text, strlen(*rep->e_text));
-
-    HMAC_Final(&ctx, rep->hash->data, 0);
-    HMAC_CTX_cleanup(&ctx);
-
-    return 0;
+    if (rep->certificate && !KX509_HMAC_OK(HMAC_Update(ctx,
+	rep->certificate->data, rep->certificate->length)))
+	goto out;
+    if (rep->e_text && !KX509_HMAC_OK(HMAC_Update(ctx,
+	(unsigned char *)*rep->e_text, strlen(*rep->e_text))))
+	goto out;
+    if (!KX509_HMAC_OK(HMAC_Final(ctx, rep->hash->data, NULL)))
+	goto out;
+    ret = 0;
+
+out:
+    KX509_HMAC_FREE(ctx);
+    if (ret && allocated) {
+	memset_s(rep->hash->data, rep->hash->length, 0, rep->hash->length);
+	krb5_data_free(rep->hash);
+    }
+    if (ret == EINVAL)
+	krb5_set_error_message(context, ret, "KX509 reply HMAC failed");
+    return ret;
 }
 
 /*
