$NetBSD$

Keep GSS NTLM message state consistent on native OpenSSL HMAC errors.
Origin: EmberBSD contributors (AI-assisted), not submitted upstream.

--- lib/gssapi/ntlm/crypto.c
+++ lib/gssapi/ntlm/crypto.c
@@ -44,6 +44,12 @@
 struct _krb5_key_type;
 #include "krb5_locl.h"
 
+#if defined(EMBERBSD_BASE_HEIMDAL) && defined(HAVE_HCRYPTO_W_OPENSSL) && \
+    defined(OPENSSL_VERSION_NUMBER) && OPENSSL_VERSION_NUMBER >= 0x10100000L && \
+    !defined(LIBRESSL_VERSION_NUMBER)
+#define HEIMNTLM_GSS_OPAQUE_HMAC 1
+#endif
+
 /*
  *
  */
@@ -154,6 +160,22 @@
 {
     unsigned char hmac[16];
     unsigned int hmaclen;
+#ifdef HEIMNTLM_GSS_OPAQUE_HMAC
+    HMAC_CTX *c = HMAC_CTX_new();
+
+    if (c == NULL)
+	return GSS_S_FAILURE;
+    encode_le_uint32(seq, hmac);
+    if (HMAC_Init_ex(c, signkey, 16, EVP_md5(), NULL) != 1 ||
+	HMAC_Update(c, hmac, 4) != 1 ||
+	HMAC_Update(c, in->value, in->length) != 1 ||
+	HMAC_Final(c, hmac, &hmaclen) != 1 || hmaclen != sizeof(hmac)) {
+	HMAC_CTX_free(c);
+	memset_s(hmac, sizeof(hmac), 0, sizeof(hmac));
+	return GSS_S_FAILURE;
+    }
+    HMAC_CTX_free(c);
+#else
     HMAC_CTX c;
 
     HMAC_CTX_init(&c);
@@ -164,6 +186,7 @@
     HMAC_Update(&c, in->value, in->length);
     HMAC_Final(&c, hmac, &hmaclen);
     HMAC_CTX_cleanup(&c);
+#endif
 
     encode_le_uint32(1, &out[0]);
     if (sealkey)
@@ -172,6 +195,9 @@
 	memcpy(&out[4], hmac, 8);
 
     memset(&out[12], 0, 4);
+#ifdef HEIMNTLM_GSS_OPAQUE_HMAC
+    memset_s(hmac, sizeof(hmac), 0, sizeof(hmac));
+#endif
 
     return GSS_S_COMPLETE;
 }
@@ -205,6 +231,9 @@
 {
     unsigned char *p;
     OM_uint32 ret;
+#ifdef HEIMNTLM_GSS_OPAQUE_HMAC
+    RC4_KEY saved_sealkey;
+#endif
 
     if (in->length + 16 < in->length)
 	return EINVAL;
@@ -213,14 +242,25 @@
     if (p == NULL)
 	return ENOMEM;
 
+#ifdef HEIMNTLM_GSS_OPAQUE_HMAC
+    saved_sealkey = *sealkey;
+#endif
     RC4(sealkey, in->length, in->value, p);
 
     ret = v2_sign_message(in, signkey, sealkey, seq, &p[in->length]);
     if (ret) {
+#ifdef HEIMNTLM_GSS_OPAQUE_HMAC
+	if (ret == GSS_S_FAILURE)
+	    *sealkey = saved_sealkey;
+	memset_s(&saved_sealkey, sizeof(saved_sealkey), 0, sizeof(saved_sealkey));
+#endif
 	free(p);
 	return ret;
     }
 
+#ifdef HEIMNTLM_GSS_OPAQUE_HMAC
+    memset_s(&saved_sealkey, sizeof(saved_sealkey), 0, sizeof(saved_sealkey));
+#endif
     out->value = p;
     out->length = in->length + 16;
 
@@ -235,6 +275,9 @@
 		  gss_buffer_t out)
 {
     OM_uint32 ret;
+#ifdef HEIMNTLM_GSS_OPAQUE_HMAC
+    RC4_KEY saved_sealkey;
+#endif
 
     if (in->length < 16)
 	return GSS_S_BAD_MIC;
@@ -244,14 +287,26 @@
     if (out->value == NULL)
 	return GSS_S_BAD_MIC;
 
+#ifdef HEIMNTLM_GSS_OPAQUE_HMAC
+    saved_sealkey = *sealkey;
+#endif
     RC4(sealkey, out->length, in->value, out->value);
 
     ret = v2_verify_message(out, signkey, sealkey, seq,
 			    ((const unsigned char *)in->value) + out->length);
     if (ret) {
 	OM_uint32 junk;
+#ifdef HEIMNTLM_GSS_OPAQUE_HMAC
+	if (ret == GSS_S_FAILURE) {
+	    *sealkey = saved_sealkey;
+	    memset_s(out->value, out->length, 0, out->length);
+	}
+#endif
 	gss_release_buffer(&junk, out);
     }
+#ifdef HEIMNTLM_GSS_OPAQUE_HMAC
+    memset_s(&saved_sealkey, sizeof(saved_sealkey), 0, sizeof(saved_sealkey));
+#endif
     return ret;
 }
 
@@ -298,8 +353,16 @@
 	ret = v2_sign_message(message_buffer,
 			      ctx->u.v2.send.signkey,
 			      ctx->u.v2.send.signsealkey,
+#ifdef HEIMNTLM_GSS_OPAQUE_HMAC
+			      ctx->u.v2.send.seq,
+#else
 			      ctx->u.v2.send.seq++,
+#endif
 			      message_token->value);
+#ifdef HEIMNTLM_GSS_OPAQUE_HMAC
+	if (ret != GSS_S_FAILURE)
+	    ctx->u.v2.send.seq++;
+#endif
 	if (ret)
 	    gss_release_buffer(&junk, message_token);
         return ret;
@@ -368,8 +431,16 @@
 	ret = v2_verify_message(message_buffer,
 				ctx->u.v2.recv.signkey,
 				ctx->u.v2.recv.signsealkey,
+#ifdef HEIMNTLM_GSS_OPAQUE_HMAC
+				ctx->u.v2.recv.seq,
+#else
 				ctx->u.v2.recv.seq++,
+#endif
 				token_buffer->value);
+#ifdef HEIMNTLM_GSS_OPAQUE_HMAC
+	if (ret != GSS_S_FAILURE)
+	    ctx->u.v2.recv.seq++;
+#endif
 	if (ret)
 	    return ret;
 
@@ -481,11 +552,20 @@
 
     if (CTX_FLAGS_ISSET(ctx, NTLM_NEG_SEAL|NTLM_NEG_NTLM2_SESSION)) {
 
-	return v2_seal_message(input_message_buffer,
+	OM_uint32 ret = v2_seal_message(input_message_buffer,
 			       ctx->u.v2.send.signkey,
+#ifdef HEIMNTLM_GSS_OPAQUE_HMAC
+			       ctx->u.v2.send.seq,
+#else
 			       ctx->u.v2.send.seq++,
+#endif
 			       &ctx->u.v2.send.sealkey,
 			       output_message_buffer);
+#ifdef HEIMNTLM_GSS_OPAQUE_HMAC
+	if (ret != GSS_S_FAILURE)
+	    ctx->u.v2.send.seq++;
+#endif
+	return ret;
 
     } else if (CTX_FLAGS_ISSET(ctx, NTLM_NEG_SEAL)) {
 	gss_buffer_desc trailer;
@@ -553,11 +633,20 @@
 
     if (CTX_FLAGS_ISSET(ctx, NTLM_NEG_SEAL|NTLM_NEG_NTLM2_SESSION)) {
 
-	return v2_unseal_message(input_message_buffer,
+	OM_uint32 ret = v2_unseal_message(input_message_buffer,
 				 ctx->u.v2.recv.signkey,
+#ifdef HEIMNTLM_GSS_OPAQUE_HMAC
+				 ctx->u.v2.recv.seq,
+#else
 				 ctx->u.v2.recv.seq++,
+#endif
 				 &ctx->u.v2.recv.sealkey,
 				 output_message_buffer);
+#ifdef HEIMNTLM_GSS_OPAQUE_HMAC
+	if (ret != GSS_S_FAILURE)
+	    ctx->u.v2.recv.seq++;
+#endif
+	return ret;
 
     } else if (CTX_FLAGS_ISSET(ctx, NTLM_NEG_SEAL)) {
 
