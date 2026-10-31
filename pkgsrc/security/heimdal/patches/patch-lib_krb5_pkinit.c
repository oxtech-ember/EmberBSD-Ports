$NetBSD$

Use OpenSSL DH accessors in the native NetBSD backend and preserve
ownership on failure. Close the moduli stream on all paths.
Origin: NetBSD crypto/external/bsd/heimdal, with EmberBSD lifecycle fixes.

--- lib/krb5/pkinit.c
+++ lib/krb5/pkinit.c
@@ -79,8 +79,14 @@
     free(cert);
 }
 
+#if defined(EMBERBSD_BASE_HEIMDAL) && defined(HAVE_HCRYPTO_W_OPENSSL) && \
+    defined(OPENSSL_VERSION_NUMBER) && OPENSSL_VERSION_NUMBER >= 0x10100000L && \
+    !defined(LIBRESSL_VERSION_NUMBER)
+#define HEIMDAL_OPAQUE_DH 1
+#endif
+
 static krb5_error_code
-BN_to_integer(krb5_context context, BIGNUM *bn, heim_integer *integer)
+BN_to_integer(krb5_context context, const BIGNUM *bn, heim_integer *integer)
 {
     integer->length = BN_num_bytes(bn);
     integer->data = malloc(integer->length);
@@ -113,7 +119,12 @@
 		struct krb5_dh_moduli **moduli)
 {
     const struct krb5_dh_moduli *m;
-
+#ifdef HEIMDAL_OPAQUE_DH
+    BIGNUM *p, *q, *g;
+#endif
+
+    if (moduli == NULL || moduli[0] == NULL)
+	return EINVAL;
     if (bits == 0) {
 	m = moduli[1]; /* XXX */
 	if (m == NULL)
@@ -134,6 +145,23 @@
 	m = moduli[i];
     }
 
+#ifdef HEIMDAL_OPAQUE_DH
+    p = integer_to_BN(context, "p", &m->p);
+    g = integer_to_BN(context, "g", &m->g);
+    q = integer_to_BN(context, "q", &m->q);
+    if (p == NULL || g == NULL || q == NULL) {
+	BN_free(p);
+	BN_free(g);
+	BN_free(q);
+	return ENOMEM;
+    }
+    if (DH_set0_pqg(dh, p, q, g) != 1) {
+	BN_free(p);
+	BN_free(g);
+	BN_free(q);
+	return EINVAL;
+    }
+#else
     dh->p = integer_to_BN(context, "p", &m->p);
     if (dh->p == NULL)
 	return ENOMEM;
@@ -143,6 +171,7 @@
     dh->q = integer_to_BN(context, "q", &m->q);
     if (dh->q == NULL)
 	return ENOMEM;
+#endif
 
     return 0;
 }
@@ -455,6 +484,14 @@
 	    DH *dh = ctx->u.dh;
 	    DomainParameters dp;
 	    heim_integer dh_pub_key;
+#ifdef HEIMDAL_OPAQUE_DH
+	    const BIGNUM *dh_p, *dh_q, *dh_g, *dh_public;
+	    DH_get0_pqg(dh, &dh_p, &dh_q, &dh_g);
+	    DH_get0_key(dh, &dh_public, NULL);
+	    if (dh_p == NULL || dh_q == NULL || dh_g == NULL ||
+		dh_public == NULL)
+		return EINVAL;
+#endif
 
 	    ret = der_copy_oid(&asn1_oid_id_dhpublicnumber,
 			       &a->clientPublicValue->algorithm.algorithm);
@@ -463,12 +500,24 @@
 
 	    memset(&dp, 0, sizeof(dp));
 
-	    ret = BN_to_integer(context, dh->p, &dp.p);
+	    ret = BN_to_integer(context,
+#ifdef HEIMDAL_OPAQUE_DH
+		dh_p,
+#else
+		dh->p,
+#endif
+		&dp.p);
 	    if (ret) {
 		free_DomainParameters(&dp);
 		return ret;
 	    }
-	    ret = BN_to_integer(context, dh->g, &dp.g);
+	    ret = BN_to_integer(context,
+#ifdef HEIMDAL_OPAQUE_DH
+		dh_g,
+#else
+		dh->g,
+#endif
+		&dp.g);
 	    if (ret) {
 		free_DomainParameters(&dp);
 		return ret;
@@ -478,7 +527,13 @@
 		free_DomainParameters(&dp);
 		return ENOMEM;
 	    }
-	    ret = BN_to_integer(context, dh->q, dp.q);
+	    ret = BN_to_integer(context,
+#ifdef HEIMDAL_OPAQUE_DH
+		dh_q,
+#else
+		dh->q,
+#endif
+		dp.q);
 	    if (ret) {
 		free_DomainParameters(&dp);
 		return ret;
@@ -503,7 +558,13 @@
 	    if (size != a->clientPublicValue->algorithm.parameters->length)
 		krb5_abortx(context, "Internal ASN1 encoder error");
 
-	    ret = BN_to_integer(context, dh->pub_key, &dh_pub_key);
+	    ret = BN_to_integer(context,
+#ifdef HEIMDAL_OPAQUE_DH
+		dh_public,
+#else
+		dh->pub_key,
+#endif
+		&dh_pub_key);
 	    if (ret)
 		return ret;
 
@@ -2210,6 +2271,7 @@
 	m2 = realloc(m, (n + 2) * sizeof(m[0]));
 	if (m2 == NULL) {
 	    _krb5_free_moduli(m);
+	    fclose(f);
 	    return krb5_enomem(context);
 	}
 	m = m2;
@@ -2219,6 +2281,7 @@
 	ret = _krb5_parse_moduli_line(context, file, lineno, buf,  &element);
 	if (ret) {
 	    _krb5_free_moduli(m);
+	    fclose(f);
 	    return ret;
 	}
 	if (element == NULL)
@@ -2228,6 +2291,7 @@
 	m[n + 1] = NULL;
 	n++;
     }
+    fclose(f);
     *moduli = m;
     return 0;
 }
