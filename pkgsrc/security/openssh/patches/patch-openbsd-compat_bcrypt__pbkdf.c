$NetBSD$

Pass the password bytes to SHA512 without changing their constness.
Origin: EmberBSD contributors (AI-assisted), not submitted upstream.

--- openbsd-compat/bcrypt_pbkdf.c
+++ openbsd-compat/bcrypt_pbkdf.c
@@ -137,7 +137,7 @@
 	memcpy(countsalt, salt, saltlen);
 
 	/* collapse password */
-	crypto_hash_sha512(sha2pass, pass, passlen);
+	crypto_hash_sha512(sha2pass, (const unsigned char *)pass, passlen);
 
 	/* generate key, sizeof(out) at a time */
 	for (count = 1; keylen > 0; count++) {
