$NetBSD$

Support opaque OpenSSL HMAC contexts for the native NetBSD backend.
Preserve KAFS derivation, check failures, and clean transient material.
Origin: NetBSD crypto/external/bsd/heimdal, with EmberBSD lifecycle fixes.

--- lib/kafs/rxkad_kdf.c
+++ lib/kafs/rxkad_kdf.c
@@ -84,24 +84,62 @@
     unsigned char tmp[64];
     unsigned int mdsize;
     DES_cblock ktmp;
-    HMAC_CTX mctx;
+#if defined(EMBERBSD_BASE_HEIMDAL) && defined(HAVE_HCRYPTO_W_OPENSSL) && \
+    defined(OPENSSL_VERSION_NUMBER) && OPENSSL_VERSION_NUMBER >= 0x10100000L && \
+    !defined(LIBRESSL_VERSION_NUMBER)
+#define HEIMDAL_KAFS_OPAQUE_HMAC 1
+    HMAC_CTX *mctx;
+#else
+    HMAC_CTX storage, *mctx = &storage;
+#endif
 
     /* stop when 8 bit counter wraps to 0 */
     for (i = 1; i; i++) {
-	HMAC_CTX_init(&mctx);
-	HMAC_Init_ex(&mctx, in, insize, EVP_md5(), NULL);
-	HMAC_Update(&mctx, &i, 1);
-	HMAC_Update(&mctx, label, sizeof(label));   /* includes label and separator */
-	HMAC_Update(&mctx, Lbuf, 4);
+#ifdef HEIMDAL_KAFS_OPAQUE_HMAC
+	mctx = HMAC_CTX_new();
+	if (mctx == NULL) {
+	    memset_s(tmp, sizeof(tmp), 0, sizeof(tmp));
+	    memset_s(ktmp, sizeof(ktmp), 0, sizeof(ktmp));
+	    return ENOMEM;
+	}
+	if (HMAC_Init_ex(mctx, in, insize, EVP_md5(), NULL) != 1 ||
+	    HMAC_Update(mctx, &i, 1) != 1 ||
+	    HMAC_Update(mctx, label, sizeof(label)) != 1 ||
+	    HMAC_Update(mctx, Lbuf, 4) != 1) {
+	    HMAC_CTX_free(mctx);
+	    memset_s(tmp, sizeof(tmp), 0, sizeof(tmp));
+	    memset_s(ktmp, sizeof(ktmp), 0, sizeof(ktmp));
+	    return EINVAL;
+	}
 	mdsize = sizeof(tmp);
-	HMAC_Final(&mctx, tmp, &mdsize);
+	if (HMAC_Final(mctx, tmp, &mdsize) != 1) {
+	    HMAC_CTX_free(mctx);
+	    memset_s(tmp, sizeof(tmp), 0, sizeof(tmp));
+	    memset_s(ktmp, sizeof(ktmp), 0, sizeof(ktmp));
+	    return EINVAL;
+	}
+	HMAC_CTX_free(mctx);
+#else
+	HMAC_CTX_init(mctx);
+	HMAC_Init_ex(mctx, in, insize, EVP_md5(), NULL);
+	HMAC_Update(mctx, &i, 1);
+	HMAC_Update(mctx, label, sizeof(label));
+	HMAC_Update(mctx, Lbuf, 4);
+	mdsize = sizeof(tmp);
+	HMAC_Final(mctx, tmp, &mdsize);
+	HMAC_CTX_cleanup(mctx);
+#endif
 	memcpy(ktmp, tmp, 8);
 	DES_set_odd_parity(&ktmp);
 	if (!DES_is_weak_key(&ktmp)) {
 	    memcpy(out, ktmp, 8);
+	    memset_s(tmp, sizeof(tmp), 0, sizeof(tmp));
+	    memset_s(ktmp, sizeof(ktmp), 0, sizeof(ktmp));
 	    return 0;
 	}
     }
+    memset_s(tmp, sizeof(tmp), 0, sizeof(tmp));
+    memset_s(ktmp, sizeof(ktmp), 0, sizeof(ktmp));
     return KRB5DES_WEAK_KEY;
 }
 
