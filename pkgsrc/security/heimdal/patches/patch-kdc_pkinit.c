$NetBSD$

Use opaque OpenSSL DH accessors in the native NetBSD backend, preserving
parameter ownership and releasing the decoded group on all failure paths.
Origin: NetBSD crypto/external/bsd/heimdal, with EmberBSD lifecycle fixes.

--- kdc/pkinit.c
+++ kdc/pkinit.c
@@ -45,6 +45,12 @@
 #include <hx509.h>
 #include "crypto-headers.h"
 
+#if defined(EMBERBSD_BASE_HEIMDAL) && defined(HAVE_HCRYPTO_W_OPENSSL) && \
+    defined(OPENSSL_VERSION_NUMBER) && OPENSSL_VERSION_NUMBER >= 0x10100000L && \
+    !defined(LIBRESSL_VERSION_NUMBER)
+#define HEIMDAL_OPAQUE_DH 1
+#endif
+
 struct pk_client_params {
     enum krb5_pk_type type;
     enum keyex_enum keyex;
@@ -298,6 +304,9 @@
 {
     DomainParameters dhparam;
     DH *dh = NULL;
+#ifdef HEIMDAL_OPAQUE_DH
+    BIGNUM *p = NULL, *g = NULL, *q = NULL;
+#endif
     krb5_error_code ret;
 
     memset(&dhparam, 0, sizeof(dhparam));
@@ -342,6 +351,24 @@
 	goto out;
     }
     ret = KRB5_BADMSGTYPE;
+#ifdef HEIMDAL_OPAQUE_DH
+    p = integer_to_BN(context, "DH prime", &dhparam.p);
+    if (p == NULL)
+	goto out;
+    g = integer_to_BN(context, "DH base", &dhparam.g);
+    if (g == NULL)
+	goto out;
+    if (dhparam.q) {
+	q = integer_to_BN(context, "DH p-1 factor", dhparam.q);
+	if (q == NULL)
+	    goto out;
+    }
+    if (DH_set0_pqg(dh, p, q, g) != 1) {
+	krb5_set_error_message(context, ret, "Cannot set DH parameters");
+	goto out;
+    }
+    p = g = q = NULL;
+#else
     dh->p = integer_to_BN(context, "DH prime", &dhparam.p);
     if (dh->p == NULL)
 	goto out;
@@ -351,9 +378,10 @@
 
     if (dhparam.q) {
 	dh->q = integer_to_BN(context, "DH p-1 factor", dhparam.q);
-	if (dh->g == NULL)
-	    goto out;
-    }
+	if (dh->q == NULL)
+	    goto out;
+    }
+#endif
 
     {
 	heim_integer glue;
@@ -365,7 +393,7 @@
 				 &size);
 	if (ret) {
 	    krb5_clear_error_message(context);
-	    return ret;
+	    goto out;
 	}
 
 	client_params->u.dh.public_key = integer_to_BN(context,
@@ -383,6 +411,11 @@
     ret = 0;
 
  out:
+#ifdef HEIMDAL_OPAQUE_DH
+    BN_free(p);
+    BN_free(g);
+    BN_free(q);
+#endif
     if (dh)
 	DH_free(dh);
     free_DomainParameters(&dhparam);
@@ -800,7 +833,7 @@
  */
 
 static krb5_error_code
-BN_to_integer(krb5_context context, BIGNUM *bn, heim_integer *integer)
+BN_to_integer(krb5_context context, const BIGNUM *bn, heim_integer *integer)
 {
     integer->length = BN_num_bytes(bn);
     integer->data = malloc(integer->length);
@@ -1017,9 +1050,19 @@
 
     if (cp->keyex == USE_DH) {
 	DH *kdc_dh = cp->u.dh.key;
+	const BIGNUM *pub_key;
 	heim_integer i;
 
-	ret = BN_to_integer(context, kdc_dh->pub_key, &i);
+#ifdef HEIMDAL_OPAQUE_DH
+	DH_get0_key(kdc_dh, &pub_key, NULL);
+#else
+	pub_key = kdc_dh->pub_key;
+#endif
+	if (pub_key == NULL) {
+	    krb5_set_error_message(context, EINVAL, "Missing PKINIT DH public key");
+	    return EINVAL;
+	}
+	ret = BN_to_integer(context, pub_key, &i);
 	if (ret)
 	    return ret;
 
