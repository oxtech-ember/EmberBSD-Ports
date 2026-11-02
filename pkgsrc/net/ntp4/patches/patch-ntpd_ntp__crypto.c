$NetBSD$

Build with OpenSSL 4: names, extensions and ASN.1 strings of a
certificate are const, and ASN1_STRING is opaque. Build a new name
for a new certificate and read strings through the accessors.
EmberBSD (AI-assisted).

--- ntpd/ntp_crypto.c.orig
+++ ntpd/ntp_crypto.c
@@ -2032,9 +2032,9 @@
 	 * Also note that two-digit years less than 50 map to years greater than
 	 * 100. Dontcha love ASN.1? Better than MIL-188.
 	 */
-	len = asn1time->length;
+	len = ASN1_STRING_length(asn1time);
 	REQUIRE(len < sizeof(v));
-	(void)strncpy(v, (char *)(asn1time->data), len);
+	(void)strncpy(v, (const char *)ASN1_STRING_get0_data(asn1time), len);
 	REQUIRE(len >= 13);
 	temp = strtoul(v+len-3, NULL, 10);
 	pjd->second = temp;
@@ -3145,7 +3145,7 @@
 {
 	X509	*req;		/* X509 certificate request */
 	X509	*cert;		/* X509 certificate */
-	X509_EXTENSION *ext;	/* certificate extension */
+	const X509_EXTENSION *ext; /* certificate extension */
 	ASN1_INTEGER *serial;	/* serial number */
 	X509_NAME *subj;	/* distinguished (common) name */
 	EVP_PKEY *pkey;		/* public key */
@@ -3198,11 +3198,12 @@
 	X509_set_serialNumber(cert, serial);
 	X509_gmtime_adj(X509_getm_notBefore(cert), 0L);
 	X509_gmtime_adj(X509_getm_notAfter(cert), YEAR);
-	subj = X509_get_issuer_name(cert);
+	subj = X509_NAME_new();
 	X509_NAME_add_entry_by_txt(subj, "commonName", MBSTRING_ASC,
 	    hostval.ptr, strlen((const char *)hostval.ptr), -1, 0);
-	subj = X509_get_subject_name(req);
-	X509_set_subject_name(cert, subj);
+	X509_set_issuer_name(cert, subj);
+	X509_NAME_free(subj);
+	X509_set_subject_name(cert, X509_get_subject_name(req));
 	X509_set_pubkey(cert, pkey);
 	temp = X509_get_ext_count(req);
 	for (i = 0; i < temp; i++) {
@@ -3515,10 +3516,10 @@
 	 */
 	cnt = X509_get_ext_count(cert);
 	for (i = 0; i < cnt; i++) {
-		X509_EXTENSION *ext;
-		ASN1_OBJECT *obj;
+		const X509_EXTENSION *ext;
+		const ASN1_OBJECT *obj;
 		int nid;
-		ASN1_OCTET_STRING *data;
+		const ASN1_OCTET_STRING *data;
 
 		ext = X509_get_ext(cert, i);
 		obj = X509_EXTENSION_get_object(ext);
@@ -3551,8 +3552,8 @@
 		 */
 		case NID_subject_key_identifier:
 			data = X509_EXTENSION_get_data(ext);
-			ret->grpkey = BN_bin2bn(&data->data[2],
-			    data->length - 2, NULL);
+			ret->grpkey = BN_bin2bn(ASN1_STRING_get0_data(data) + 2,
+			    ASN1_STRING_length(data) - 2, NULL);
 			/* fall through */
 		default:
 			DPRINTF(1, ("cert_parse: %s\n",
