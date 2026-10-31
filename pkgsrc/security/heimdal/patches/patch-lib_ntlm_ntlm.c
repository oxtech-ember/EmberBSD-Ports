$NetBSD$

Use checked NTLM crypto contexts in the native NetBSD backend; propagate
crypto errors through the checked NTLM session API. Update ABI version.
Origin: NetBSD crypto/external/bsd/heimdal with EmberBSD lifecycle and API fixes.

--- lib/ntlm/ntlm.c
+++ lib/ntlm/ntlm.c
@@ -57,6 +57,27 @@
 
 #include <heimntlm.h>
 
+#if defined(EMBERBSD_BASE_HEIMDAL) && defined(HAVE_HCRYPTO_W_OPENSSL) && \
+    defined(OPENSSL_VERSION_NUMBER) && OPENSSL_VERSION_NUMBER >= 0x10100000L && \
+    !defined(LIBRESSL_VERSION_NUMBER)
+#define HEIMNTLM_OPAQUE_OPENSSL 1
+#define NTLM_HMAC_DECLARE(name) HMAC_CTX *name
+#define NTLM_HMAC_INIT(name) (((name) = HMAC_CTX_new()) != NULL)
+#define NTLM_HMAC_FREE(name) HMAC_CTX_free(name)
+#define NTLM_HMAC_OK(expr) ((expr) == 1)
+#define NTLM_CIPHER_DECLARE(name) EVP_CIPHER_CTX *name
+#define NTLM_CIPHER_INIT(name) (((name) = EVP_CIPHER_CTX_new()) != NULL)
+#define NTLM_CIPHER_FREE(name) EVP_CIPHER_CTX_free(name)
+#else
+#define NTLM_HMAC_DECLARE(name) HMAC_CTX name##_storage, *name = &name##_storage
+#define NTLM_HMAC_INIT(name) (HMAC_CTX_init(name), 1)
+#define NTLM_HMAC_FREE(name) do { HMAC_CTX_cleanup(name); memset(name, 0, sizeof(*(name))); } while (0)
+#define NTLM_HMAC_OK(expr) ((expr), 1)
+#define NTLM_CIPHER_DECLARE(name) EVP_CIPHER_CTX name##_storage, *name = &name##_storage
+#define NTLM_CIPHER_INIT(name) (EVP_CIPHER_CTX_init(name), 1)
+#define NTLM_CIPHER_FREE(name) EVP_CIPHER_CTX_cleanup(name)
+#endif
+
 /*! \mainpage Heimdal NTLM library
  *
  * \section intro Introduction
@@ -354,7 +375,7 @@
 	utf8len += 1;
 	
 	*s = malloc(utf8len);
-	if (s == NULL) {
+	if (*s == NULL) {
 	    ret = ENOMEM;
 	    goto out;
 	}
@@ -1170,13 +1191,14 @@
  *
  */
 
-static void
+static int
 splitandenc(unsigned char *hash,
 	    unsigned char *challenge,
 	    unsigned char *answer)
 {
-    EVP_CIPHER_CTX ctx;
+    NTLM_CIPHER_DECLARE(ctx);
     unsigned char key[8];
+    int ret = HNTLM_ERR_CRYPTO;
 
     key[0] =  hash[0];
     key[1] = (hash[0] << 7) | (hash[1] >> 1);
@@ -1187,12 +1209,16 @@
     key[6] = (hash[5] << 2) | (hash[6] >> 6);
     key[7] = (hash[6] << 1);
 
-    EVP_CIPHER_CTX_init(&ctx);
-
-    EVP_CipherInit_ex(&ctx, EVP_des_cbc(), NULL, key, NULL, 1);
-    EVP_Cipher(&ctx, answer, challenge, 8);
-    EVP_CIPHER_CTX_cleanup(&ctx);
+    if (!NTLM_CIPHER_INIT(ctx)) {
+	memset_s(key, sizeof(key), 0, sizeof(key));
+	return ENOMEM;
+    }
+    if (EVP_CipherInit_ex(ctx, EVP_des_cbc(), NULL, key, NULL, 1) == 1 &&
+        EVP_Cipher(ctx, answer, challenge, 8) > 0)
+	ret = 0;
+    NTLM_CIPHER_FREE(ctx);
     memset_s(key, sizeof(key), 0, sizeof(key));
+    return ret;
 }
 
 /**
@@ -1261,6 +1287,7 @@
 			  struct ntlm_buf *answer)
 {
     unsigned char res[21];
+    int ret;
 
     if (len != MD4_DIGEST_LENGTH)
 	return HNTLM_ERR_INVALID_LENGTH;
@@ -1273,11 +1300,15 @@
 	return ENOMEM;
     answer->length = 24;
 
-    splitandenc(&res[0],  challenge, ((unsigned char *)answer->data) + 0);
-    splitandenc(&res[7],  challenge, ((unsigned char *)answer->data) + 8);
-    splitandenc(&res[14], challenge, ((unsigned char *)answer->data) + 16);
-
-    return 0;
+    ret = splitandenc(&res[0], challenge, ((unsigned char *)answer->data));
+    if (ret == 0)
+	ret = splitandenc(&res[7], challenge, ((unsigned char *)answer->data) + 8);
+    if (ret == 0)
+	ret = splitandenc(&res[14], challenge, ((unsigned char *)answer->data) + 16);
+    memset_s(res, sizeof(res), 0, sizeof(res));
+    if (ret != 0)
+	heim_ntlm_free_buf(answer);
+    return ret;
 }
 
 int
@@ -1312,7 +1343,8 @@
 			  struct ntlm_buf *session)
 {
     unsigned int hmaclen;
-    HMAC_CTX c;
+    NTLM_HMAC_DECLARE(c);
+    int ret = 0;
 
     if (ntlmResponse->length <= 16)
         return HNTLM_ERR_INVALID_LENGTH;
@@ -1323,13 +1355,18 @@
     session->length = 16;
 
     /* Note: key is the NTLMv2 key */
-    HMAC_CTX_init(&c);
-    HMAC_Init_ex(&c, key, len, EVP_md5(), NULL);
-    HMAC_Update(&c, ntlmResponse->data, 16);
-    HMAC_Final(&c, session->data, &hmaclen);
-    HMAC_CTX_cleanup(&c);
-
-    return 0;
+    if (!NTLM_HMAC_INIT(c)) {
+	heim_ntlm_free_buf(session);
+	return ENOMEM;
+    }
+    if (!NTLM_HMAC_OK(HMAC_Init_ex(c, key, len, EVP_md5(), NULL)) ||
+        !NTLM_HMAC_OK(HMAC_Update(c, ntlmResponse->data, 16)) ||
+        !NTLM_HMAC_OK(HMAC_Final(c, session->data, &hmaclen)))
+	ret = HNTLM_ERR_CRYPTO;
+    NTLM_HMAC_FREE(c);
+    if (ret != 0)
+	heim_ntlm_free_buf(session);
+    return ret;
 }
 
 
@@ -1338,7 +1375,7 @@
 		     struct ntlm_buf *session,
 		     struct ntlm_buf *encryptedSession)
 {
-    EVP_CIPHER_CTX c;
+    NTLM_CIPHER_DECLARE(c);
     int ret;
 
     if (base_session->length != MD4_DIGEST_LENGTH)
@@ -1358,26 +1395,36 @@
 	return ENOMEM;
     }
 
-    EVP_CIPHER_CTX_init(&c);
+    if (!NTLM_CIPHER_INIT(c)) {
+	heim_ntlm_free_buf(encryptedSession);
+	heim_ntlm_free_buf(session);
+	return ENOMEM;
+    }
 
-    ret = EVP_CipherInit_ex(&c, EVP_rc4(), NULL, base_session->data, NULL, 1);
+    ret = EVP_CipherInit_ex(c, EVP_rc4(), NULL, base_session->data, NULL, 1);
     if (ret != 1) {
-	EVP_CIPHER_CTX_cleanup(&c);
+	NTLM_CIPHER_FREE(c);
 	heim_ntlm_free_buf(encryptedSession);
 	heim_ntlm_free_buf(session);
 	return HNTLM_ERR_CRYPTO;
     }
 
     if (RAND_bytes(session->data, session->length) != 1) {
-	EVP_CIPHER_CTX_cleanup(&c);
+	memset_s(session->data, session->length, 0, session->length);
+	NTLM_CIPHER_FREE(c);
 	heim_ntlm_free_buf(encryptedSession);
 	heim_ntlm_free_buf(session);
 	return HNTLM_ERR_RAND;
     }
 
-    EVP_Cipher(&c, encryptedSession->data, session->data, encryptedSession->length);
-    EVP_CIPHER_CTX_cleanup(&c);
-
+    ret = EVP_Cipher(c, encryptedSession->data, session->data, encryptedSession->length);
+    NTLM_CIPHER_FREE(c);
+    if (ret <= 0) {
+	memset_s(session->data, session->length, 0, session->length);
+	heim_ntlm_free_buf(encryptedSession);
+	heim_ntlm_free_buf(session);
+	return HNTLM_ERR_CRYPTO;
+    }
     return 0;
 
 
@@ -1469,7 +1516,8 @@
 		       struct ntlm_buf *encryptedSession,
 		       struct ntlm_buf *session)
 {
-    EVP_CIPHER_CTX c;
+    NTLM_CIPHER_DECLARE(c);
+    int ret;
 
     memset(session, 0, sizeof(*session));
 
@@ -1484,17 +1532,24 @@
 	session->length = 0;
 	return ENOMEM;
     }
-    EVP_CIPHER_CTX_init(&c);
+    if (!NTLM_CIPHER_INIT(c)) {
+	heim_ntlm_free_buf(session);
+	return ENOMEM;
+    }
 
-    if (EVP_CipherInit_ex(&c, EVP_rc4(), NULL, baseKey->data, NULL, 0) != 1) {
-	EVP_CIPHER_CTX_cleanup(&c);
+    if (EVP_CipherInit_ex(c, EVP_rc4(), NULL, baseKey->data, NULL, 0) != 1) {
+	NTLM_CIPHER_FREE(c);
 	heim_ntlm_free_buf(session);
 	return HNTLM_ERR_CRYPTO;
     }
 
-    EVP_Cipher(&c, session->data, encryptedSession->data, session->length);
-    EVP_CIPHER_CTX_cleanup(&c);
-
+    ret = EVP_Cipher(c, session->data, encryptedSession->data, session->length);
+    NTLM_CIPHER_FREE(c);
+    if (ret <= 0) {
+	memset_s(session->data, session->length, 0, session->length);
+	heim_ntlm_free_buf(session);
+	return HNTLM_ERR_CRYPTO;
+    }
     return 0;
 }
 
@@ -1523,29 +1578,41 @@
 {
     int ret;
     unsigned int hmaclen;
-    HMAC_CTX c;
+    NTLM_HMAC_DECLARE(c);
 
-    HMAC_CTX_init(&c);
-    HMAC_Init_ex(&c, key, len, EVP_md5(), NULL);
+    if (!NTLM_HMAC_INIT(c)) {
+	memset_s(ntlmv2, 16, 0, 16);
+	return ENOMEM;
+    }
+    if (!NTLM_HMAC_OK(HMAC_Init_ex(c, key, len, EVP_md5(), NULL))) {
+	ret = HNTLM_ERR_CRYPTO;
+	goto out;
+    }
     {
 	struct ntlm_buf buf;
 	/* uppercase username and turn it into ucs2-le */
 	ret = ascii2ucs2le(username, 1, &buf);
 	if (ret)
 	    goto out;
-	HMAC_Update(&c, buf.data, buf.length);
+	ret = NTLM_HMAC_OK(HMAC_Update(c, buf.data, buf.length)) ? 0 : HNTLM_ERR_CRYPTO;
 	free(buf.data);
+	if (ret != 0)
+	    goto out;
 	/* turn target into ucs2-le */
 	ret = ascii2ucs2le(target, upper_case_target, &buf);
 	if (ret)
 	    goto out;
-	HMAC_Update(&c, buf.data, buf.length);
+	ret = NTLM_HMAC_OK(HMAC_Update(c, buf.data, buf.length)) ? 0 : HNTLM_ERR_CRYPTO;
 	free(buf.data);
+	if (ret != 0)
+	    goto out;
     }
-    HMAC_Final(&c, ntlmv2, &hmaclen);
+    if (!NTLM_HMAC_OK(HMAC_Final(c, ntlmv2, &hmaclen)))
+	ret = HNTLM_ERR_CRYPTO;
  out:
-    HMAC_CTX_cleanup(&c);
-    memset(&c, 0, sizeof(c));
+    NTLM_HMAC_FREE(c);
+    if (ret != 0)
+	memset_s(ntlmv2, 16, 0, 16);
 
     return ret;
 }
@@ -1599,21 +1666,28 @@
 			struct ntlm_buf *answer)
 {
     unsigned char clientchallenge[8];
+    int ret;
 
     if (RAND_bytes(clientchallenge, sizeof(clientchallenge)) != 1)
 	return HNTLM_ERR_RAND;
 
     /* calculate ntlmv2 key */
 
-    heim_ntlm_ntlmv2_key(key, len, username, target, 0, ntlmv2);
+    ret = heim_ntlm_ntlmv2_key(key, len, username, target, 0, ntlmv2);
+    if (ret != 0)
+	return ret;
 
     answer->data = malloc(24);
     if (answer->data == NULL)
         return ENOMEM;
     answer->length = 24;
 
-    heim_ntlm_derive_ntlm2_sess(ntlmv2, clientchallenge, 8,
-				serverchallenge, answer->data);
+    ret = heim_ntlm_derive_ntlm2_sess(ntlmv2, clientchallenge, 8,
+				       serverchallenge, answer->data);
+    if (ret != 0) {
+	heim_ntlm_free_buf(answer);
+	return ret;
+    }
 
     memcpy(((unsigned char *)answer->data) + 16, clientchallenge, 8);
 
@@ -1662,7 +1736,9 @@
 
     /* calculate ntlmv2 key */
 
-    heim_ntlm_ntlmv2_key(key, len, username, target, 0, ntlmv2);
+    ret = heim_ntlm_ntlmv2_key(key, len, username, target, 0, ntlmv2);
+    if (ret != 0)
+	return ret;
 
     /* calculate and build ntlmv2 answer */
 
@@ -1695,7 +1771,12 @@
     krb5_storage_free(sp);
     sp = NULL;
 
-    heim_ntlm_derive_ntlm2_sess(ntlmv2, data.data, data.length, serverchallenge, ntlmv2answer);
+    ret = heim_ntlm_derive_ntlm2_sess(ntlmv2, data.data, data.length,
+				       serverchallenge, ntlmv2answer);
+    if (ret != 0) {
+	krb5_data_free(&data);
+	return ret;
+    }
 
     sp = krb5_storage_emem();
     if (sp == NULL) {
@@ -1754,7 +1835,9 @@
 
     /* calculate ntlmv2 key */
 
-    heim_ntlm_ntlmv2_key(key, len, username, target, upper_case_target, ntlmv2);
+    ret = heim_ntlm_ntlmv2_key(key, len, username, target, upper_case_target, ntlmv2);
+    if (ret != 0)
+	return ret;
 
     /* calculate and build ntlmv2 answer */
 
@@ -1809,10 +1892,11 @@
 	goto out;
     }
 
-    heim_ntlm_derive_ntlm2_sess(ntlmv2,
-				((unsigned char *)answer->data) + 16, answer->length - 16,
-				serverchallenge,
-				serveranswer);
+    ret = heim_ntlm_derive_ntlm2_sess(ntlmv2,
+				      ((unsigned char *)answer->data) + 16, answer->length - 16,
+				      serverchallenge, serveranswer);
+    if (ret != 0)
+	goto out;
 
     if (memcmp(serveranswer, clientanswer, 16) != 0) {
 	heim_ntlm_free_buf(infotarget);
@@ -1936,11 +2020,17 @@
     memcpy(res, ntlm_hash, 16);
 
     resp = ntlm->data;
-    splitandenc(&res[0], ntlm2_sess_hash, resp + 0);
-    splitandenc(&res[7], ntlm2_sess_hash, resp + 8);
-    splitandenc(&res[14], ntlm2_sess_hash, resp + 16);
-
-    return 0;
+    code = splitandenc(&res[0], ntlm2_sess_hash, resp);
+    if (code == 0)
+	code = splitandenc(&res[7], ntlm2_sess_hash, resp + 8);
+    if (code == 0)
+	code = splitandenc(&res[14], ntlm2_sess_hash, resp + 16);
+    memset_s(res, sizeof(res), 0, sizeof(res));
+    if (code != 0) {
+	heim_ntlm_free_buf(lm);
+	heim_ntlm_free_buf(ntlm);
+    }
+    return code;
 }
 
 
@@ -1995,21 +2085,28 @@
  * @ingroup ntlm_core
  */
 
-void
+int
 heim_ntlm_derive_ntlm2_sess(const unsigned char sessionkey[16],
 			    const unsigned char *clnt_nonce, size_t clnt_nonce_length,
 			    const unsigned char svr_chal[8],
 			    unsigned char derivedkey[16])
 {
     unsigned int hmaclen;
-    HMAC_CTX c;
+    NTLM_HMAC_DECLARE(c);
+    int ret = 0;
 
     /* HMAC(Ksession, serverchallenge || clientchallenge) */
-    HMAC_CTX_init(&c);
-    HMAC_Init_ex(&c, sessionkey, 16, EVP_md5(), NULL);
-    HMAC_Update(&c, svr_chal, 8);
-    HMAC_Update(&c, clnt_nonce, clnt_nonce_length);
-    HMAC_Final(&c, derivedkey, &hmaclen);
-    HMAC_CTX_cleanup(&c);
-    memset(&c, 0, sizeof(c));
+    if (!NTLM_HMAC_INIT(c)) {
+	memset_s(derivedkey, 16, 0, 16);
+	return ENOMEM;
+    }
+    if (!NTLM_HMAC_OK(HMAC_Init_ex(c, sessionkey, 16, EVP_md5(), NULL)) ||
+        !NTLM_HMAC_OK(HMAC_Update(c, svr_chal, 8)) ||
+        !NTLM_HMAC_OK(HMAC_Update(c, clnt_nonce, clnt_nonce_length)) ||
+        !NTLM_HMAC_OK(HMAC_Final(c, derivedkey, &hmaclen)))
+	ret = HNTLM_ERR_CRYPTO;
+    NTLM_HMAC_FREE(c);
+    if (ret != 0)
+	memset_s(derivedkey, 16, 0, 16);
+    return ret;
 }
