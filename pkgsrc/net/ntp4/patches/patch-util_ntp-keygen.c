$NetBSD$

Build with OpenSSL 4: names, extensions and ASN.1 strings of a
certificate are const, and ASN1_STRING is opaque. Build a new name
for a new certificate and read strings through the accessors.
EmberBSD (AI-assisted).

--- util/ntp-keygen.c.orig
+++ util/ntp-keygen.c
@@ -541,8 +541,8 @@
 			ptr = strstr(groupbuf, "CN=");
 			cnt = X509_get_ext_count(cert);
 			for (i = 0; i < cnt; i++) {
-				X509_EXTENSION *ext;
-				ASN1_OBJECT *obj;
+				const X509_EXTENSION *ext;
+				const ASN1_OBJECT *obj;
 
 				ext = X509_get_ext(cert, i);
 				obj = X509_EXTENSION_get_object(ext);
@@ -2001,12 +2001,12 @@
 	ASN1_INTEGER_free(serial);
 	X509_time_adj(X509_getm_notBefore(cert), 0L, &epoch);
 	X509_time_adj(X509_getm_notAfter(cert), lifetime * SECSPERDAY, &epoch);
-	subj = X509_get_subject_name(cert);
-	X509_NAME_add_entry_by_txt(subj, "commonName", MBSTRING_ASC,
-	    (u_char *)name, -1, -1, 0);
-	subj = X509_get_issuer_name(cert);
+	subj = X509_NAME_new();
 	X509_NAME_add_entry_by_txt(subj, "commonName", MBSTRING_ASC,
 	    (u_char *)name, -1, -1, 0);
+	X509_set_subject_name(cert, subj);
+	X509_set_issuer_name(cert, subj);
+	X509_NAME_free(subj);
 	if (!X509_set_pubkey(cert, pkey)) {
 		fprintf(stderr, "Assign certificate signing key fails\n%s\n",
 		    ERR_error_string(ERR_get_error(), NULL));
