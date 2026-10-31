$NetBSD$

Origin: EmberBSD contributors (AI-assisted), not submitted upstream.

Use non-deprecated ASN.1 read-only accessors with OpenSSL 4.1.

--- smallapp/unbound-anchor.c
+++ smallapp/unbound-anchor.c
@@ -1703,6 +1703,21 @@
 	}
 }
 
+#if !defined(HAVE_X509_GET_KEY_USAGE) || !defined(HAVE_X509_NAME_GET_TEXT_BY_NID) || defined(DEPRECATED_X509_NAME_GET_TEXT_BY_NID)
+/* ASN1_STRING_get_length is available in OpenSSL 4.1 and returns size_t. */
+static size_t
+anchor_asn1_length(const ASN1_STRING* s)
+{
+#if !defined(LIBRESSL_VERSION_NUMBER) && OPENSSL_VERSION_NUMBER >= 0x40100000L
+	return ASN1_STRING_get_length(s);
+#else
+	int len = ASN1_STRING_length(s);
+	return len > 0 ? (size_t)len : 0;
+#endif
+}
+
+#endif
+
 /* get key usage out of its extension, returns 0 if no key_usage extension */
 static unsigned long
 get_usage_of_ex(X509* cert)
@@ -1715,12 +1730,12 @@
 #else
 	ASN1_BIT_STRING* s;
 	if((s=X509_get_ext_d2i(cert, NID_key_usage, NULL, NULL))) {
-#  ifdef HAVE_ASN1_STRING_GET0_DATA
+#  if defined(HAVE_ASN1_STRING_GET0_DATA) || (!defined(LIBRESSL_VERSION_NUMBER) && OPENSSL_VERSION_NUMBER >= 0x10100000L)
 		const unsigned char *data = ASN1_STRING_get0_data(s);
 #  else
 		const unsigned char *data = ASN1_STRING_data(s);
 #  endif
-		int len = ASN1_STRING_length(s);
+		size_t len = anchor_asn1_length(s);
 		if(len > 0) {
 			val = data[0];
 			if(len > 1)
@@ -1761,15 +1776,16 @@
 		if(!ne) continue;
 		asn = X509_NAME_ENTRY_get_data(ne);
 		if(!asn) continue;
-#  ifdef HAVE_ASN1_STRING_GET0_DATA
+#  if defined(HAVE_ASN1_STRING_GET0_DATA) || (!defined(LIBRESSL_VERSION_NUMBER) && OPENSSL_VERSION_NUMBER >= 0x10100000L)
 		data = ASN1_STRING_get0_data(asn);
 #  else
 		data = ASN1_STRING_data(asn);
 #  endif
 		if(!data) continue;
-		if(ASN1_STRING_length(asn) > (int)sizeof(buf)-1) continue;
-		memcpy(buf, data, ASN1_STRING_length(asn));
-		buf[ASN1_STRING_length(asn)]=0;
+		size_t len = anchor_asn1_length(asn);
+		if(len >= sizeof(buf)) continue;
+		memcpy(buf, data, len);
+		buf[len]=0;
 		printf("%s: %s\n", str, buf);
 	}
 }
@@ -1804,13 +1820,13 @@
 		if(!ne) continue;
 		asn = X509_NAME_ENTRY_get_data(ne);
 		if(!asn) continue;
-#  ifdef HAVE_ASN1_STRING_GET0_DATA
+#  if defined(HAVE_ASN1_STRING_GET0_DATA) || (!defined(LIBRESSL_VERSION_NUMBER) && OPENSSL_VERSION_NUMBER >= 0x10100000L)
 		data = ASN1_STRING_get0_data(asn);
 #  else
 		data = ASN1_STRING_data(asn);
 #  endif
 		if(!data) continue;
-		if(ASN1_STRING_length(asn) == (int)strlen(p7signer) &&
+		if(anchor_asn1_length(asn) == strlen(p7signer) &&
 			strncmp((char*)data, p7signer, strlen(p7signer)) == 0)
 			return 1; /* match */
 	}
