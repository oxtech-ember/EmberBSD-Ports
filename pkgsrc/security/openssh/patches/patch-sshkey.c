$NetBSD$

Keep read-only key and passphrase inputs const with OpenSSL 4.
Origin: EmberBSD contributors (AI-assisted), not submitted upstream.

--- sshkey.c
+++ sshkey.c
@@ -1142,7 +1142,7 @@
 	 * Chars to be used after each other every time the worm
 	 * intersects with itself.  Matter of taste.
 	 */
-	char	*augmentation_string = " .o+=*BOX@%&#/^SE";
+	const char *augmentation_string = " .o+=*BOX@%&#/^SE";
 	char	*retval, *p, title[FLDSIZE_X], hash[FLDSIZE_X];
 	u_char	 field[FLDSIZE_X][FLDSIZE_Y];
 	size_t	 i, tlen, hlen;
@@ -3031,7 +3031,7 @@
 	}
 
 	/* decode base64 */
-	if ((r = sshbuf_b64tod(decoded, (char *)sshbuf_ptr(encoded))) != 0)
+	if ((r = sshbuf_b64tod(decoded, (const char *)sshbuf_ptr(encoded))) != 0)
 		goto out;
 
 	/* check magic */
@@ -3320,7 +3320,11 @@
 	int was_shielded = sshkey_is_shielded(key);
 	int success, r;
 	int blen, len = strlen(_passphrase);
+#if OPENSSL_VERSION_NUMBER >= 0x40000000L && !defined(LIBRESSL_VERSION_NUMBER)
+	const u_char *passphrase = (len > 0) ? (const u_char *)_passphrase : NULL;
+#else
 	u_char *passphrase = (len > 0) ? (u_char *)_passphrase : NULL;
+#endif
 	const EVP_CIPHER *cipher = (len > 0) ? EVP_aes_128_cbc() : NULL;
 	char *bptr;
 	BIO *bio = NULL;
@@ -3523,7 +3527,7 @@
 static int
 pem_passphrase_cb(char *buf, int size, int rwflag, void *u)
 {
-	char *p = (char *)u;
+	const char *p = u == NULL ? NULL : *(const char *const *)u;
 	size_t len;
 
 	if (p == NULL || (len = strlen(p)) == 0)
@@ -3558,7 +3562,7 @@
 
 	clear_libcrypto_errors();
 	if ((pk = PEM_read_bio_PrivateKey(bio, NULL, pem_passphrase_cb,
-	    (char *)passphrase)) == NULL) {
+	    &passphrase)) == NULL) {
 		/*
 		 * libcrypto may return various ASN.1 errors when attempting
 		 * to parse a key with an incorrect passphrase.
