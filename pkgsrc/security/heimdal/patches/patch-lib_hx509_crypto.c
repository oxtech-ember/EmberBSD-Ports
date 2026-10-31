$NetBSD$

Use accessors and opaque cipher contexts for the selected NetBSD native
OpenSSL backend. Preserve legacy hcrypto paths and handle setter ownership
and context cleanup explicitly.
Origin: NetBSD crypto/external/bsd/heimdal/dist/lib/hx509/crypto.c;
EmberBSD ownership and error-handling adaptation (AI-assisted).

--- lib/hx509/crypto.c.orig
+++ lib/hx509/crypto.c
@@ -1,3 +1,5 @@
+/*	$NetBSD: crypto.c,v 1.4 2023/06/19 21:41:44 christos Exp $	*/
+
 /*
  * Copyright (c) 2004 - 2016 Kungliga Tekniska Högskolan
  * (Royal Institute of Technology, Stockholm, Sweden).
@@ -33,6 +35,12 @@
 
 #include "hx_locl.h"
 
+#if defined(__NetBSD__) && defined(EMBERBSD_BASE_HEIMDAL) && \
+    defined(HAVE_HCRYPTO_W_OPENSSL) && !defined(LIBRESSL_VERSION_NUMBER) && \
+    OPENSSL_VERSION_NUMBER >= 0x10100000UL
+#define HEIMDAL_NATIVE_OPAQUE_OPENSSL 1
+#endif
+
 /*-
  * RFC5758 specifies no parameters for ecdsa-with-SHA<N> signatures
  * RFC5754 specifies NULL parameters for sha<N>WithRSAEncryption signatures
@@ -271,6 +279,7 @@
 	{
 	    ret = HX509_CRYPTO_SIG_INVALID_FORMAT;
 	    hx509_set_error_string(context, 0, ret, "RSA Signature incorrect");
+	    free(to);
 	    goto out;
 	}
 	free(to);
@@ -550,9 +559,21 @@
 		 const char *type)
 {
     if (strcasecmp(type, "rsa-modulus") == 0) {
-	return BN_dup(key->private_key.rsa->n);
+	const BIGNUM *n;
+#if !defined(HEIMDAL_NATIVE_OPAQUE_OPENSSL)
+	n = key->private_key.rsa->n;
+#else
+	RSA_get0_key(key->private_key.rsa, &n, NULL, NULL);
+#endif
+	return BN_dup(n);
     } else if (strcasecmp(type, "rsa-exponent") == 0) {
-	return BN_dup(key->private_key.rsa->e);
+	const BIGNUM *e;
+#if !defined(HEIMDAL_NATIVE_OPAQUE_OPENSSL)
+	e = key->private_key.rsa->e;
+#else
+	RSA_get0_key(key->private_key.rsa, NULL, &e, NULL);
+#endif
+	return BN_dup(e);
     } else
 	return NULL;
 }
@@ -603,14 +624,24 @@
     if (ret)
 	goto out;
 
-    dsa->pub_key = heim_int2BN(&pk);
-
-    free_DSAPublicKey(&pk);
-
-    if (dsa->pub_key == NULL) {
-	ret = ENOMEM;
-	hx509_set_error_string(context, 0, ret, "out of memory");
-	goto out;
+    {
+        BIGNUM *pub = heim_int2BN(&pk);
+        free_DSAPublicKey(&pk);
+        if (pub == NULL) {
+            ret = ENOMEM;
+            hx509_set_error_string(context, 0, ret, "out of memory");
+            goto out;
+        }
+#if !defined(HEIMDAL_NATIVE_OPAQUE_OPENSSL)
+        dsa->pub_key = pub;
+#else
+        if (DSA_set0_key(dsa, pub, NULL) != 1) {
+            BN_free(pub);
+            ret = ENOMEM;
+            hx509_set_error_string(context, 0, ret, "failed to set DSA public key");
+            goto out;
+        }
+#endif
     }
 
     if (spi->algorithm.parameters == NULL) {
@@ -628,16 +659,29 @@
 	goto out;
     }
 
-    dsa->p = heim_int2BN(&param.p);
-    dsa->q = heim_int2BN(&param.q);
-    dsa->g = heim_int2BN(&param.g);
-
-    free_DSAParams(&param);
-
-    if (dsa->p == NULL || dsa->q == NULL || dsa->g == NULL) {
-	ret = ENOMEM;
-	hx509_set_error_string(context, 0, ret, "out of memory");
-	goto out;
+    {
+        BIGNUM *p = heim_int2BN(&param.p);
+        BIGNUM *q = heim_int2BN(&param.q);
+        BIGNUM *g = heim_int2BN(&param.g);
+        free_DSAParams(&param);
+        if (p == NULL || q == NULL || g == NULL) {
+            BN_free(p); BN_free(q); BN_free(g);
+            ret = ENOMEM;
+            hx509_set_error_string(context, 0, ret, "out of memory");
+            goto out;
+        }
+#if !defined(HEIMDAL_NATIVE_OPAQUE_OPENSSL)
+        dsa->p = p;
+        dsa->q = q;
+        dsa->g = g;
+#else
+        if (DSA_set0_pqg(dsa, p, q, g) != 1) {
+            BN_free(p); BN_free(q); BN_free(g);
+            ret = ENOMEM;
+            hx509_set_error_string(context, 0, ret, "failed to set DSA parameters");
+            goto out;
+        }
+#endif
     }
 
     ret = DSA_verify(-1, data->data, data->length,
@@ -2067,24 +2111,33 @@
 		     const heim_octet_string *ivec,
 		     heim_octet_string **ciphertext)
 {
-    EVP_CIPHER_CTX evp;
+    EVP_CIPHER_CTX *evp;
     size_t padsize, bsize;
     int ret;
 
+#if !defined(HEIMDAL_NATIVE_OPAQUE_OPENSSL)
+    EVP_CIPHER_CTX ectx;
+#endif
     *ciphertext = NULL;
 
     if ((crypto->cipher->flags & CIPHER_WEAK) &&
 	(crypto->flags & ALLOW_WEAK) == 0)
 	return HX509_CRYPTO_ALGORITHM_BEST_BEFORE;
+#if !defined(HEIMDAL_NATIVE_OPAQUE_OPENSSL)
+    evp = &ectx;
+    EVP_CIPHER_CTX_init(evp);
+#else
+    evp = EVP_CIPHER_CTX_new();
+    if (evp == NULL)
+        return ENOMEM;
+#endif
 
     assert(EVP_CIPHER_iv_length(crypto->c) == (int)ivec->length);
 
-    EVP_CIPHER_CTX_init(&evp);
-
-    ret = EVP_CipherInit_ex(&evp, crypto->c, NULL,
+
+    ret = EVP_CipherInit_ex(evp, crypto->c, NULL,
 			    crypto->key.data, ivec->data, 1);
     if (ret != 1) {
-	EVP_CIPHER_CTX_cleanup(&evp);
 	ret = HX509_CRYPTO_INTERNAL_ERROR;
 	goto out;
     }
@@ -2101,21 +2154,28 @@
     padsize = 0;
 
     if (crypto->flags & PADDING_NONE) {
-	if (bsize != 1 && (length % bsize) != 0)
-	    return HX509_CMS_PADDING_ERROR;
+	if (bsize != 1 && (length % bsize) != 0) {
+	    ret = HX509_CMS_PADDING_ERROR;
+	    goto out;
+	}
     } else if (crypto->flags & PADDING_PKCS7) {
 	if (bsize != 1)
 	    padsize = bsize - (length % bsize);
     }
 
     (*ciphertext)->length = length + padsize;
+#if defined(HEIMDAL_NATIVE_OPAQUE_OPENSSL)
+    (*ciphertext)->data = malloc(length + padsize ? length + padsize : 1);
+#else
     (*ciphertext)->data = malloc(length + padsize);
+#endif
     if ((*ciphertext)->data == NULL) {
 	ret = ENOMEM;
 	goto out;
     }
 
-    memcpy((*ciphertext)->data, data, length);
+    if (length != 0)
+        memcpy((*ciphertext)->data, data, length);
     if (padsize) {
 	size_t i;
 	unsigned char *p = (*ciphertext)->data;
@@ -2124,10 +2184,18 @@
 	    *p++ = padsize;
     }
 
-    ret = EVP_Cipher(&evp, (*ciphertext)->data,
-		     (*ciphertext)->data,
-		     length + padsize);
+#if defined(HEIMDAL_NATIVE_OPAQUE_OPENSSL)
+    ret = length + padsize == 0 ? 1 : EVP_Cipher(evp, (*ciphertext)->data,
+                                                (*ciphertext)->data, length + padsize);
+#else
+    ret = EVP_Cipher(evp, (*ciphertext)->data,
+                     (*ciphertext)->data, length + padsize);
+#endif
+#if defined(HEIMDAL_NATIVE_OPAQUE_OPENSSL)
+    if (ret <= 0) {
+#else
     if (ret != 1) {
+#endif
 	ret = HX509_CRYPTO_INTERNAL_ERROR;
 	goto out;
     }
@@ -2143,7 +2211,11 @@
 	    *ciphertext = NULL;
 	}
     }
-    EVP_CIPHER_CTX_cleanup(&evp);
+#if !defined(HEIMDAL_NATIVE_OPAQUE_OPENSSL)
+    EVP_CIPHER_CTX_cleanup(evp);
+#else
+    EVP_CIPHER_CTX_free(evp);
+#endif
 
     return ret;
 }
@@ -2155,7 +2227,7 @@
 		     heim_octet_string *ivec,
 		     heim_octet_string *clear)
 {
-    EVP_CIPHER_CTX evp;
+    EVP_CIPHER_CTX *evp;
     void *idata = NULL;
     int ret;
 
@@ -2175,27 +2247,69 @@
     if (ivec)
 	idata = ivec->data;
 
-    EVP_CIPHER_CTX_init(&evp);
-
-    ret = EVP_CipherInit_ex(&evp, crypto->c, NULL,
+#if !defined(HEIMDAL_NATIVE_OPAQUE_OPENSSL)
+    EVP_CIPHER_CTX ectx;
+    evp = &ectx;
+    EVP_CIPHER_CTX_init(evp);
+#else
+    evp = EVP_CIPHER_CTX_new();
+    if (evp == NULL)
+        return ENOMEM;
+#endif
+
+    ret = EVP_CipherInit_ex(evp, crypto->c, NULL,
 			    crypto->key.data, idata, 0);
     if (ret != 1) {
-	EVP_CIPHER_CTX_cleanup(&evp);
+#if !defined(HEIMDAL_NATIVE_OPAQUE_OPENSSL)
+	EVP_CIPHER_CTX_cleanup(evp);
+#else
+	EVP_CIPHER_CTX_free(evp);
+#endif
 	return HX509_CRYPTO_INTERNAL_ERROR;
     }
 
     clear->length = length;
+#if defined(HEIMDAL_NATIVE_OPAQUE_OPENSSL)
+    clear->data = malloc(length ? length : 1);
+#else
     clear->data = malloc(length);
+#endif
     if (clear->data == NULL) {
-	EVP_CIPHER_CTX_cleanup(&evp);
+#if !defined(HEIMDAL_NATIVE_OPAQUE_OPENSSL)
+	EVP_CIPHER_CTX_cleanup(evp);
+#else
+	EVP_CIPHER_CTX_free(evp);
+#endif
 	clear->length = 0;
 	return ENOMEM;
     }
 
-    if (EVP_Cipher(&evp, clear->data, data, length) != 1) {
-	return HX509_CRYPTO_INTERNAL_ERROR;
-    }
-    EVP_CIPHER_CTX_cleanup(&evp);
+#if defined(HEIMDAL_NATIVE_OPAQUE_OPENSSL)
+    ret = length == 0 ? 1 : EVP_Cipher(evp, clear->data, data, length);
+#else
+    ret = EVP_Cipher(evp, clear->data, data, length);
+#endif
+#if defined(HEIMDAL_NATIVE_OPAQUE_OPENSSL)
+    if (ret <= 0) {
+#else
+    if (ret != 1) {
+#endif
+#if !defined(HEIMDAL_NATIVE_OPAQUE_OPENSSL)
+        EVP_CIPHER_CTX_cleanup(evp);
+#else
+        EVP_CIPHER_CTX_free(evp);
+#endif
+        memset_s(clear->data, clear->length, 0, clear->length);
+        free(clear->data);
+        clear->data = NULL;
+        clear->length = 0;
+        return HX509_CRYPTO_INTERNAL_ERROR;
+    }
+#if !defined(HEIMDAL_NATIVE_OPAQUE_OPENSSL)
+    EVP_CIPHER_CTX_cleanup(evp);
+#else
+    EVP_CIPHER_CTX_free(evp);
+#endif
 
     if ((crypto->flags & PADDING_PKCS7) && EVP_CIPHER_block_size(crypto->c) > 1) {
 	int padsize;
@@ -2467,6 +2581,68 @@
  */
 
 
+#if defined(HEIMDAL_NATIVE_OPAQUE_OPENSSL)
+static int
+match_keys_rsa(hx509_cert c, hx509_private_key private_key)
+{
+    const Certificate *cert;
+    const SubjectPublicKeyInfo *spi;
+    const BIGNUM *d = NULL, *p = NULL, *q = NULL;
+    const BIGNUM *dmp1 = NULL, *dmq1 = NULL, *iqmp = NULL;
+    BIGNUM *n = NULL, *e = NULL, *copy_d = NULL, *copy_p = NULL, *copy_q = NULL;
+    BIGNUM *copy_dmp1 = NULL, *copy_dmq1 = NULL, *copy_iqmp = NULL;
+    RSAPublicKey pk;
+    RSA *rsa = NULL, *key = private_key->private_key.rsa;
+    size_t size;
+    int ok = 0;
+
+    if (key == NULL)
+        return 0;
+    RSA_get0_key(key, NULL, NULL, &d);
+    RSA_get0_factors(key, &p, &q);
+    RSA_get0_crt_params(key, &dmp1, &dmq1, &iqmp);
+    if (d == NULL || p == NULL || q == NULL || dmp1 == NULL || dmq1 == NULL)
+        return 0;
+    cert = _hx509_get_cert(c);
+    spi = &cert->tbsCertificate.subjectPublicKeyInfo;
+    rsa = RSA_new();
+    if (rsa == NULL)
+        return 0;
+    if (decode_RSAPublicKey(spi->subjectPublicKey.data,
+                           spi->subjectPublicKey.length / 8, &pk, &size))
+        goto out;
+    n = heim_int2BN(&pk.modulus);
+    e = heim_int2BN(&pk.publicExponent);
+    free_RSAPublicKey(&pk);
+    copy_d = BN_dup(d); copy_p = BN_dup(p); copy_q = BN_dup(q);
+    if (iqmp != NULL) {
+        copy_dmp1 = BN_dup(dmp1); copy_dmq1 = BN_dup(dmq1);
+        copy_iqmp = BN_dup(iqmp);
+    }
+    if (n == NULL || e == NULL || copy_d == NULL || copy_p == NULL ||
+        copy_q == NULL || (iqmp != NULL &&
+        (copy_dmp1 == NULL || copy_dmq1 == NULL || copy_iqmp == NULL)))
+        goto out;
+    if (RSA_set0_key(rsa, n, e, copy_d) != 1)
+        goto out;
+    n = e = copy_d = NULL;
+    if (RSA_set0_factors(rsa, copy_p, copy_q) != 1)
+        goto out;
+    copy_p = copy_q = NULL;
+    if (iqmp != NULL) {
+        if (RSA_set0_crt_params(rsa, copy_dmp1, copy_dmq1, copy_iqmp) != 1)
+            goto out;
+        copy_dmp1 = copy_dmq1 = copy_iqmp = NULL;
+    }
+    ok = RSA_check_key(rsa) == 1;
+out:
+    BN_free(n); BN_free(e); BN_clear_free(copy_d);
+    BN_clear_free(copy_p); BN_clear_free(copy_q);
+    BN_clear_free(copy_dmp1); BN_clear_free(copy_dmq1); BN_clear_free(copy_iqmp);
+    RSA_free(rsa);
+    return ok;
+}
+#else
 static int
 match_keys_rsa(hx509_cert c, hx509_private_key private_key)
 {
@@ -2522,6 +2698,7 @@
 
     return ret == 1;
 }
+#endif /* native opaque OpenSSL */
 
 static int
 match_keys_ec(hx509_cert c, hx509_private_key private_key)
