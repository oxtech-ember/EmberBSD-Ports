$NetBSD: patch-lib_gssapi_krb5_arcfour.c,v 1.1 2023/02/08 07:41:25 wiz Exp $

Fix for CVE-2022-45142 from Helmut Grohne <helmut@subdivi.de>

Preserve the NetBSD base backend with checked cipher lifecycle.

--- lib/gssapi/krb5/arcfour.c
+++ lib/gssapi/krb5/arcfour.c
@@ -237,7 +237,6 @@
     int32_t seq_number;
     size_t len, total_len;
     u_char k6_data[16], *p0, *p;
-    EVP_CIPHER_CTX rc4_key;
 
     _gsskrb5_encap_length (22, &len, &total_len, GSS_KRB5_MECHANISM);
 
@@ -291,19 +290,26 @@
 				     &seq_number);
     p = p0 + 8; /* SND_SEQ */
     _gsskrb5_encode_be_om_uint32(seq_number, p);
-
-    krb5_auth_con_setlocalseqnumber (context,
-				     context_handle->auth_context,
-				     ++seq_number);
+#ifndef GSSKRB5_OPAQUE_CIPHER
+    krb5_auth_con_setlocalseqnumber(context, context_handle->auth_context, ++seq_number);
     HEIMDAL_MUTEX_unlock(&context_handle->ctx_id_mutex);
+#endif
 
     memset (p + 4, (context_handle->more_flags & LOCAL) ? 0 : 0xff, 4);
 
-    EVP_CIPHER_CTX_init(&rc4_key);
-    EVP_CipherInit_ex(&rc4_key, EVP_rc4(), NULL, k6_data, NULL, 1);
-    EVP_Cipher(&rc4_key, p, p, 8);
-    EVP_CIPHER_CTX_cleanup(&rc4_key);
+    ret = gsskrb5_cipher_once(EVP_rc4(), k6_data, NULL, 1, p, p, 8);
+    if (ret) {
+        HEIMDAL_MUTEX_unlock(&context_handle->ctx_id_mutex);
+        memset_s(k6_data, sizeof(k6_data), 0, sizeof(k6_data));
+        _gsskrb5_release_buffer(minor_status, message_token);
+        *minor_status = ret;
+        return GSS_S_FAILURE;
+    }
 
+#ifdef GSSKRB5_OPAQUE_CIPHER
+    krb5_auth_con_setlocalseqnumber(context, context_handle->auth_context, ++seq_number);
+    HEIMDAL_MUTEX_unlock(&context_handle->ctx_id_mutex);
+#endif
     memset_s(k6_data, sizeof(k6_data), 0, sizeof(k6_data));
 
     *minor_status = 0;
@@ -365,19 +371,19 @@
 	return GSS_S_FAILURE;
     }
 
-    cmp = (ct_memcmp(cksum_data, p + 8, 8) == 0);
+    cmp = (ct_memcmp(cksum_data, p + 8, 8) != 0);
     if (cmp) {
 	*minor_status = 0;
 	return GSS_S_BAD_MIC;
     }
 
     {
-	EVP_CIPHER_CTX rc4_key;
-
-	EVP_CIPHER_CTX_init(&rc4_key);
-	EVP_CipherInit_ex(&rc4_key, EVP_rc4(), NULL, (void *)k6_data, NULL, 0);
-	EVP_Cipher(&rc4_key, SND_SEQ, p, 8);
-	EVP_CIPHER_CTX_cleanup(&rc4_key);
+	ret = gsskrb5_cipher_once(EVP_rc4(), k6_data, NULL, 0, SND_SEQ, p, 8);
+	if (ret) {
+	    memset_s(k6_data, sizeof(k6_data), 0, sizeof(k6_data));
+	    *minor_status = ret;
+	    return GSS_S_FAILURE;
+	}
 
 	memset(k6_data, 0, sizeof(k6_data));
     }
@@ -471,11 +477,10 @@
 				     &seq_number);
 
     _gsskrb5_encode_be_om_uint32(seq_number, p0 + 8);
-
-    krb5_auth_con_setlocalseqnumber (context,
-				     context_handle->auth_context,
-				     ++seq_number);
+#ifndef GSSKRB5_OPAQUE_CIPHER
+    krb5_auth_con_setlocalseqnumber(context, context_handle->auth_context, ++seq_number);
     HEIMDAL_MUTEX_unlock(&context_handle->ctx_id_mutex);
+#endif
 
     memset (p0 + 8 + 4,
 	    (context_handle->more_flags & LOCAL) ? 0 : 0xff,
@@ -500,6 +505,9 @@
     if (ret) {
 	*minor_status = ret;
 	_gsskrb5_release_buffer(minor_status, output_message_buffer);
+#ifdef GSSKRB5_OPAQUE_CIPHER
+	HEIMDAL_MUTEX_unlock(&context_handle->ctx_id_mutex);
+#endif
 	return GSS_S_FAILURE;
     }
 
@@ -520,17 +528,24 @@
     if (ret) {
 	_gsskrb5_release_buffer(minor_status, output_message_buffer);
 	*minor_status = ret;
+#ifdef GSSKRB5_OPAQUE_CIPHER
+	HEIMDAL_MUTEX_unlock(&context_handle->ctx_id_mutex);
+#endif
 	return GSS_S_FAILURE;
     }
 
 
     if(conf_req_flag) {
-	EVP_CIPHER_CTX rc4_key;
-
-	EVP_CIPHER_CTX_init(&rc4_key);
-	EVP_CipherInit_ex(&rc4_key, EVP_rc4(), NULL, k6_data, NULL, 1);
-	EVP_Cipher(&rc4_key, p0 + 24, p0 + 24, 8 + datalen);
-	EVP_CIPHER_CTX_cleanup(&rc4_key);
+	ret = gsskrb5_cipher_once(EVP_rc4(), k6_data, NULL, 1, p0 + 24, p0 + 24, 8 + datalen);
+	if (ret) {
+	    memset_s(k6_data, sizeof(k6_data), 0, sizeof(k6_data));
+	    _gsskrb5_release_buffer(minor_status, output_message_buffer);
+	    *minor_status = ret;
+#ifdef GSSKRB5_OPAQUE_CIPHER
+	    HEIMDAL_MUTEX_unlock(&context_handle->ctx_id_mutex);
+#endif
+	    return GSS_S_FAILURE;
+	}
     }
     memset(k6_data, 0, sizeof(k6_data));
 
@@ -540,19 +555,31 @@
     if (ret) {
 	_gsskrb5_release_buffer(minor_status, output_message_buffer);
 	*minor_status = ret;
+#ifdef GSSKRB5_OPAQUE_CIPHER
+	HEIMDAL_MUTEX_unlock(&context_handle->ctx_id_mutex);
+#endif
 	return GSS_S_FAILURE;
     }
 
     {
-	EVP_CIPHER_CTX rc4_key;
-
-	EVP_CIPHER_CTX_init(&rc4_key);
-	EVP_CipherInit_ex(&rc4_key, EVP_rc4(), NULL, k6_data, NULL, 1);
-	EVP_Cipher(&rc4_key, p0 + 8, p0 + 8 /* SND_SEQ */, 8);
-	EVP_CIPHER_CTX_cleanup(&rc4_key);
+	ret = gsskrb5_cipher_once(EVP_rc4(), k6_data, NULL, 1, p0 + 8, p0 + 8 /* SND_SEQ */, 8);
+	if (ret) {
+	    memset_s(k6_data, sizeof(k6_data), 0, sizeof(k6_data));
+	    _gsskrb5_release_buffer(minor_status, output_message_buffer);
+	    *minor_status = ret;
+#ifdef GSSKRB5_OPAQUE_CIPHER
+	    HEIMDAL_MUTEX_unlock(&context_handle->ctx_id_mutex);
+#endif
+	    return GSS_S_FAILURE;
+	}
 	memset_s(k6_data, sizeof(k6_data), 0, sizeof(k6_data));
     }
 
+#ifdef GSSKRB5_OPAQUE_CIPHER
+    krb5_auth_con_setlocalseqnumber(context, context_handle->auth_context, ++seq_number);
+    HEIMDAL_MUTEX_unlock(&context_handle->ctx_id_mutex);
+#endif
+
     if (conf_state)
 	*conf_state = conf_req_flag;
 
@@ -644,12 +671,12 @@
     }
 
     {
-	EVP_CIPHER_CTX rc4_key;
-
-	EVP_CIPHER_CTX_init(&rc4_key);
-	EVP_CipherInit_ex(&rc4_key, EVP_rc4(), NULL, k6_data, NULL, 1);
-	EVP_Cipher(&rc4_key, SND_SEQ, p0 + 8, 8);
-	EVP_CIPHER_CTX_cleanup(&rc4_key);
+	ret = gsskrb5_cipher_once(EVP_rc4(), k6_data, NULL, 1, SND_SEQ, p0 + 8, 8);
+	if (ret) {
+	    memset_s(k6_data, sizeof(k6_data), 0, sizeof(k6_data));
+	    *minor_status = ret;
+	    return GSS_S_FAILURE;
+	}
 	memset_s(k6_data, sizeof(k6_data), 0, sizeof(k6_data));
     }
 
@@ -692,13 +719,21 @@
     output_message_buffer->length = datalen;
 
     if(conf_flag) {
-	EVP_CIPHER_CTX rc4_key;
-
-	EVP_CIPHER_CTX_init(&rc4_key);
-	EVP_CipherInit_ex(&rc4_key, EVP_rc4(), NULL, k6_data, NULL, 1);
-	EVP_Cipher(&rc4_key, Confounder, p0 + 24, 8);
-	EVP_Cipher(&rc4_key, output_message_buffer->value, p0 + GSS_ARCFOUR_WRAP_TOKEN_SIZE, datalen);
-	EVP_CIPHER_CTX_cleanup(&rc4_key);
+	gsskrb5_cipher_ctx rc4_key;
+	ret = gsskrb5_cipher_init(&rc4_key, EVP_rc4(), k6_data, NULL, 1);
+	if (!ret) {
+	    ret = gsskrb5_cipher_update(&rc4_key, Confounder, p0 + 24, 8);
+	    if (!ret)
+	        ret = gsskrb5_cipher_update(&rc4_key, output_message_buffer->value, p0 + GSS_ARCFOUR_WRAP_TOKEN_SIZE, datalen);
+	    gsskrb5_cipher_free(&rc4_key);
+	}
+	if (ret) {
+	    memset_s(k6_data, sizeof(k6_data), 0, sizeof(k6_data));
+	    memset_s(output_message_buffer->value, output_message_buffer->length, 0, output_message_buffer->length);
+	    _gsskrb5_release_buffer(minor_status, output_message_buffer);
+	    *minor_status = ret;
+	    return GSS_S_FAILURE;
+	}
     } else {
 	memcpy(Confounder, p0 + 24, 8); /* Confounder */
 	memcpy(output_message_buffer->value,
@@ -730,7 +765,7 @@
 	return GSS_S_FAILURE;
     }
 
-    cmp = (ct_memcmp(cksum_data, p0 + 16, 8) == 0); /* SGN_CKSUM */
+    cmp = (ct_memcmp(cksum_data, p0 + 16, 8) != 0); /* SGN_CKSUM */
     if (cmp) {
 	_gsskrb5_release_buffer(minor_status, output_message_buffer);
 	*minor_status = 0;
@@ -937,7 +972,7 @@
     size_t header_len = 0;
     size_t data_len = 0;
     krb5_keyblock Klocal;
-    int i;
+    int i, sequence_locked = 0;
 
     header = _gk_find_buffer(iov, iov_count, GSS_IOV_BUFFER_TYPE_HEADER);
     padding = _gk_find_buffer(iov, iov_count, GSS_IOV_BUFFER_TYPE_PADDING);
@@ -1036,15 +1071,16 @@
     p = NULL;
 
     HEIMDAL_MUTEX_lock(&ctx->ctx_id_mutex);
+    sequence_locked = 1;
     krb5_auth_con_getlocalseqnumber(context,
 				    ctx->auth_context,
 				    &seq_number);
     _gsskrb5_encode_be_om_uint32(seq_number, p0 + 8);
-
-    krb5_auth_con_setlocalseqnumber(context,
-				    ctx->auth_context,
-				    ++seq_number);
+#ifndef GSSKRB5_OPAQUE_CIPHER
+    krb5_auth_con_setlocalseqnumber(context, ctx->auth_context, ++seq_number);
     HEIMDAL_MUTEX_unlock(&ctx->ctx_id_mutex);
+    sequence_locked = 0;
+#endif
 
     memset(p0 + 8 + 4,
            (ctx->more_flags & LOCAL) ? 0 : 0xff,
@@ -1084,34 +1120,26 @@
     }
 
     if (conf_req_flag) {
-	EVP_CIPHER_CTX rc4_key;
-
-	EVP_CIPHER_CTX_init(&rc4_key);
-	EVP_CipherInit_ex(&rc4_key, EVP_rc4(), NULL, k6_data, NULL, 1);
-
-	/* Confounder */
-	EVP_Cipher(&rc4_key, p0 + 24, p0 + 24, 8);
-
-	/* Seal Data */
-	for (i=0; i < iov_count; i++) {
-	    switch (GSS_IOV_BUFFER_TYPE(iov[i].type)) {
-	    case GSS_IOV_BUFFER_TYPE_DATA:
-		break;
-	    default:
-		continue;
+	gsskrb5_cipher_ctx rc4_key;
+	kret = gsskrb5_cipher_init(&rc4_key, EVP_rc4(), k6_data, NULL, 1);
+	if (!kret) {
+	    kret = gsskrb5_cipher_update(&rc4_key, p0 + 24, p0 + 24, 8);
+	    for (i = 0; !kret && i < iov_count; i++) {
+	        if (GSS_IOV_BUFFER_TYPE(iov[i].type) == GSS_IOV_BUFFER_TYPE_DATA)
+	            kret = gsskrb5_cipher_update(&rc4_key, iov[i].buffer.value,
+	                                         iov[i].buffer.value, iov[i].buffer.length);
 	    }
-
-	    EVP_Cipher(&rc4_key, iov[i].buffer.value,
-		       iov[i].buffer.value, iov[i].buffer.length);
+	    if (!kret && padding)
+	        kret = gsskrb5_cipher_update(&rc4_key, padding->buffer.value,
+	                                     padding->buffer.value, padding->buffer.length);
+	    gsskrb5_cipher_free(&rc4_key);
 	}
-
-	/* Padding */
-	if (padding) {
-	    EVP_Cipher(&rc4_key, padding->buffer.value,
-		       padding->buffer.value, padding->buffer.length);
+	if (kret) {
+	    memset_s(k6_data, sizeof(k6_data), 0, sizeof(k6_data));
+	    *minor_status = kret;
+	    major_status = GSS_S_FAILURE;
+	    goto failure;
 	}
-
-	EVP_CIPHER_CTX_cleanup(&rc4_key);
     }
     memset(k6_data, 0, sizeof(k6_data));
 
@@ -1121,20 +1149,27 @@
     if (kret) {
 	*minor_status = kret;
 	major_status = GSS_S_FAILURE;
-        return major_status;
+        goto failure;
     }
 
     {
-	EVP_CIPHER_CTX rc4_key;
-
-	EVP_CIPHER_CTX_init(&rc4_key);
-	EVP_CipherInit_ex(&rc4_key, EVP_rc4(), NULL, k6_data, NULL, 1);
-	EVP_Cipher(&rc4_key, p0 + 8, p0 + 8, 8); /* SND_SEQ */
-	EVP_CIPHER_CTX_cleanup(&rc4_key);
+	kret = gsskrb5_cipher_once(EVP_rc4(), k6_data, NULL, 1, p0 + 8, p0 + 8, 8);
+	if (kret) {
+	    memset_s(k6_data, sizeof(k6_data), 0, sizeof(k6_data));
+	    *minor_status = kret;
+	    major_status = GSS_S_FAILURE;
+	    goto failure;
+	}
 
 	memset(k6_data, 0, sizeof(k6_data));
     }
 
+#ifdef GSSKRB5_OPAQUE_CIPHER
+    krb5_auth_con_setlocalseqnumber(context, ctx->auth_context, ++seq_number);
+    HEIMDAL_MUTEX_unlock(&ctx->ctx_id_mutex);
+    sequence_locked = 0;
+#endif
+
     if (conf_state)
 	*conf_state = conf_req_flag;
 
@@ -1142,6 +1177,8 @@
     return GSS_S_COMPLETE;
 
 failure:
+    if (sequence_locked)
+        HEIMDAL_MUTEX_unlock(&ctx->ctx_id_mutex);
 
     gss_release_iov_buffer(&junk, iov, iov_count);
 
@@ -1266,12 +1303,12 @@
     }
 
     {
-	EVP_CIPHER_CTX rc4_key;
-
-	EVP_CIPHER_CTX_init(&rc4_key);
-	EVP_CipherInit_ex(&rc4_key, EVP_rc4(), NULL, k6_data, NULL, 1);
-	EVP_Cipher(&rc4_key, snd_seq, p0 + 8, 8); /* SND_SEQ */
-	EVP_CIPHER_CTX_cleanup(&rc4_key);
+	kret = gsskrb5_cipher_once(EVP_rc4(), k6_data, NULL, 1, snd_seq, p0 + 8, 8);
+	if (kret) {
+	    memset_s(k6_data, sizeof(k6_data), 0, sizeof(k6_data));
+	    *minor_status = kret;
+	    return GSS_S_FAILURE;
+	}
 
 	memset(k6_data, 0, sizeof(k6_data));
     }
@@ -1309,34 +1346,25 @@
     }
 
     if (conf_state == 1) {
-	EVP_CIPHER_CTX rc4_key;
-
-	EVP_CIPHER_CTX_init(&rc4_key);
-	EVP_CipherInit_ex(&rc4_key, EVP_rc4(), NULL, k6_data, NULL, 1);
-
-	/* Confounder */
-	EVP_Cipher(&rc4_key, Confounder, p0 + 24, 8);
-
-	/* Data */
-	for (i = 0; i < iov_count; i++) {
-	    switch (GSS_IOV_BUFFER_TYPE(iov[i].type)) {
-	    case GSS_IOV_BUFFER_TYPE_DATA:
-		break;
-	    default:
-		continue;
+	gsskrb5_cipher_ctx rc4_key;
+	kret = gsskrb5_cipher_init(&rc4_key, EVP_rc4(), k6_data, NULL, 1);
+	if (!kret) {
+	    kret = gsskrb5_cipher_update(&rc4_key, Confounder, p0 + 24, 8);
+	    for (i = 0; !kret && i < iov_count; i++) {
+	        if (GSS_IOV_BUFFER_TYPE(iov[i].type) == GSS_IOV_BUFFER_TYPE_DATA)
+	            kret = gsskrb5_cipher_update(&rc4_key, iov[i].buffer.value,
+	                                         iov[i].buffer.value, iov[i].buffer.length);
 	    }
-
-	    EVP_Cipher(&rc4_key, iov[i].buffer.value,
-		       iov[i].buffer.value, iov[i].buffer.length);
+	    if (!kret && padding)
+	        kret = gsskrb5_cipher_update(&rc4_key, padding->buffer.value,
+	                                     padding->buffer.value, padding->buffer.length);
+	    gsskrb5_cipher_free(&rc4_key);
 	}
-
-	/* Padding */
-	if (padding) {
-	    EVP_Cipher(&rc4_key, padding->buffer.value,
-		       padding->buffer.value, padding->buffer.length);
+	if (kret) {
+	    memset_s(k6_data, sizeof(k6_data), 0, sizeof(k6_data));
+	    *minor_status = kret;
+	    return GSS_S_FAILURE;
 	}
-
-	EVP_CIPHER_CTX_cleanup(&rc4_key);
     } else {
 	/* Confounder */
 	memcpy(Confounder, p0 + 24, 8);
