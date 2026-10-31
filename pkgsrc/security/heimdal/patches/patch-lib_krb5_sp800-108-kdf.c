$NetBSD$

Support opaque OpenSSL HMAC contexts in the native NetBSD backend,
including explicit allocation and operation errors.
Origin: NetBSD crypto/external/bsd/heimdal, with EmberBSD lifecycle fixes.

--- lib/krb5/sp800-108-kdf.c
+++ lib/krb5/sp800-108-kdf.c
@@ -56,7 +56,14 @@
 			 const EVP_MD *md,
 			 krb5_data *kdf_K0)
 {
-    HMAC_CTX c;
+#if defined(EMBERBSD_BASE_HEIMDAL) && defined(HAVE_HCRYPTO_W_OPENSSL) && \
+    defined(OPENSSL_VERSION_NUMBER) && OPENSSL_VERSION_NUMBER >= 0x10100000L && \
+    !defined(LIBRESSL_VERSION_NUMBER)
+#define HEIMDAL_OPAQUE_HMAC 1
+    HMAC_CTX *c;
+#else
+    HMAC_CTX storage, *c = &storage;
+#endif
     unsigned char *p = kdf_K0->data;
     size_t i, n, left = kdf_K0->length;
     unsigned char hmac[EVP_MAX_MD_SIZE];
@@ -65,7 +72,13 @@
 
     heim_assert(md != NULL, "SP800-108 KDF internal error");
 
-    HMAC_CTX_init(&c);
+#ifdef HEIMDAL_OPAQUE_HMAC
+    c = HMAC_CTX_new();
+    if (c == NULL)
+	return krb5_enomem(context);
+#else
+    HMAC_CTX_init(c);
+#endif
 
     n = L / h;
 
@@ -73,25 +86,52 @@
 	unsigned char tmp[4];
 	size_t len;
 
-	HMAC_Init_ex(&c, kdf_K1->data, kdf_K1->length, md, NULL);
+#ifdef HEIMDAL_OPAQUE_HMAC
+	if (HMAC_Init_ex(c, kdf_K1->data, kdf_K1->length, md, NULL) != 1)
+	    goto crypto_error;
+	_krb5_put_int(tmp, i + 1, 4);
+	if (HMAC_Update(c, tmp, 4) != 1 ||
+	    HMAC_Update(c, kdf_label->data, kdf_label->length) != 1 ||
+	    HMAC_Update(c, (unsigned char *)"", 1) != 1 ||
+	    (kdf_context && HMAC_Update(c, kdf_context->data, kdf_context->length) != 1))
+	    goto crypto_error;
+	_krb5_put_int(tmp, L * 8, 4);
+	if (HMAC_Update(c, tmp, 4) != 1 || HMAC_Final(c, hmac, &h) != 1)
+	    goto crypto_error;
+#else
+	HMAC_Init_ex(c, kdf_K1->data, kdf_K1->length, md, NULL);
 
 	_krb5_put_int(tmp, i + 1, 4);
-	HMAC_Update(&c, tmp, 4);
-	HMAC_Update(&c, kdf_label->data, kdf_label->length);
-	HMAC_Update(&c, (unsigned char *)"", 1);
+	HMAC_Update(c, tmp, 4);
+	HMAC_Update(c, kdf_label->data, kdf_label->length);
+	HMAC_Update(c, (unsigned char *)"", 1);
 	if (kdf_context)
-	    HMAC_Update(&c, kdf_context->data, kdf_context->length);
+	    HMAC_Update(c, kdf_context->data, kdf_context->length);
 	_krb5_put_int(tmp, L * 8, 4);
-	HMAC_Update(&c, tmp, 4);
+	HMAC_Update(c, tmp, 4);
 
-	HMAC_Final(&c, hmac, &h);
+	HMAC_Final(c, hmac, &h);
+#endif
 	len = h > left ? left : h;
 	memcpy(p, hmac, len);
 	p += len;
 	left -= len;
     }
 
-    HMAC_CTX_cleanup(&c);
+#ifdef HEIMDAL_OPAQUE_HMAC
+    memset_s(hmac, sizeof(hmac), 0, sizeof(hmac));
+    HMAC_CTX_free(c);
+#else
+    HMAC_CTX_cleanup(c);
+#endif
 
     return 0;
+#ifdef HEIMDAL_OPAQUE_HMAC
+crypto_error:
+    if (kdf_K0->length != 0)
+	memset_s(kdf_K0->data, kdf_K0->length, 0, kdf_K0->length);
+    memset_s(hmac, sizeof(hmac), 0, sizeof(hmac));
+    HMAC_CTX_free(c);
+    return EINVAL;
+#endif
 }
