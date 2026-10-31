$NetBSD$

Use opaque EVP contexts for native NTLM session-key unwrapping and check
cryptographic failures. Use checked RAND_bytes for native challenges.
Origin: NetBSD crypto/external/bsd/heimdal, with EmberBSD lifecycle fixes.

--- kdc/digest.c
+++ kdc/digest.c
@@ -36,6 +36,45 @@
 
 #ifdef DIGEST
 
+#if defined(EMBERBSD_BASE_HEIMDAL) && defined(HAVE_HCRYPTO_W_OPENSSL) && \
+    defined(OPENSSL_VERSION_NUMBER) && OPENSSL_VERSION_NUMBER >= 0x10100000L && \
+    !defined(LIBRESSL_VERSION_NUMBER)
+#define HEIMDAL_OPAQUE_EVP 1
+#endif
+
+static krb5_error_code
+ntlm_unwrap_sessionkey(krb5_context context, const unsigned char *sessionkey,
+    const unsigned char *encrypted, unsigned char *masterkey, size_t len)
+{
+#ifdef HEIMDAL_OPAQUE_EVP
+    EVP_CIPHER_CTX *rc4;
+    krb5_error_code ret = 0;
+
+    rc4 = EVP_CIPHER_CTX_new();
+    if (rc4 == NULL) {
+	memset_s(masterkey, len, 0, len);
+	return krb5_enomem(context);
+    }
+    if (EVP_CipherInit_ex(rc4, EVP_rc4(), NULL, sessionkey, NULL, 1) != 1 ||
+	EVP_Cipher(rc4, masterkey, encrypted, len) <= 0) {
+	ret = EINVAL;
+	memset_s(masterkey, len, 0, len);
+	krb5_set_error_message(context, ret, "NTLM session key unwrap failed");
+    }
+    EVP_CIPHER_CTX_free(rc4);
+    return ret;
+#else
+    EVP_CIPHER_CTX rc4;
+
+    (void)context;
+    EVP_CIPHER_CTX_init(&rc4);
+    EVP_CipherInit_ex(&rc4, EVP_rc4(), NULL, sessionkey, NULL, 1);
+    EVP_Cipher(&rc4, masterkey, encrypted, len);
+    EVP_CIPHER_CTX_cleanup(&rc4);
+    return 0;
+#endif
+}
+
 #define MS_CHAP_V2	0x20
 #define CHAP_MD5	0x10
 #define DIGEST_MD5	0x08
@@ -375,8 +414,18 @@
     case choice_DigestReqInner_init: {
 	unsigned char server_nonce[16], identifier;
 
+#ifdef HEIMDAL_OPAQUE_EVP
+	if (RAND_bytes(&identifier, sizeof(identifier)) != 1 ||
+	    RAND_bytes(server_nonce, sizeof(server_nonce)) != 1) {
+	    ret = EINVAL;
+	    krb5_set_error_message(context, ret,
+		"Failed to generate digest challenge");
+	    goto failed;
+	}
+#else
 	RAND_pseudo_bytes(&identifier, sizeof(identifier));
 	RAND_pseudo_bytes(server_nonce, sizeof(server_nonce));
+#endif
 
 	server_nonce[0] = kdc_time & 0xff;
 	server_nonce[1] = (kdc_time >> 8) & 0xff;
@@ -1338,7 +1387,6 @@
 
 	if (ireq.u.ntlmRequest.sessionkey) {
 	    unsigned char masterkey[MD4_DIGEST_LENGTH];
-	    EVP_CIPHER_CTX rc4;
 	    size_t len;
 
 	    if ((flags & NTLM_NEG_KEYEX) == 0) {
@@ -1359,23 +1407,23 @@
 	    }
 
 
-	    EVP_CIPHER_CTX_init(&rc4);
-	    EVP_CipherInit_ex(&rc4, EVP_rc4(), NULL, sessionkey, NULL, 1);
-	    EVP_Cipher(&rc4,
-		       masterkey, ireq.u.ntlmRequest.sessionkey->data,
-		       sizeof(masterkey));
-	    EVP_CIPHER_CTX_cleanup(&rc4);
+	    ret = ntlm_unwrap_sessionkey(context, sessionkey,
+		ireq.u.ntlmRequest.sessionkey->data, masterkey, sizeof(masterkey));
+	    if (ret)
+		goto failed;
 
 	    r.u.ntlmResponse.sessionkey =
 		malloc(sizeof(*r.u.ntlmResponse.sessionkey));
 	    if (r.u.ntlmResponse.sessionkey == NULL) {
-		ret = EINVAL;
+		memset_s(masterkey, sizeof(masterkey), 0, sizeof(masterkey));
+		ret = ENOMEM;
 		krb5_set_error_message(context, ret, "malloc: out of memory");
 		goto out;
 	    }
 
 	    ret = krb5_data_copy(r.u.ntlmResponse.sessionkey,
 				 masterkey, sizeof(masterkey));
+	    memset_s(masterkey, sizeof(masterkey), 0, sizeof(masterkey));
 	    if (ret) {
 		krb5_set_error_message(context, ret, "malloc: out of memory");
 		goto out;
