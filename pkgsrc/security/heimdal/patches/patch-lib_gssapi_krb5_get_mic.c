$NetBSD$

Support opaque OpenSSL contexts in the native Heimdal GSS backend.
Origin: NetBSD Heimdal adaptation; EmberBSD lifecycle and error handling.

--- lib/gssapi/krb5/get_mic.c
+++ lib/gssapi/krb5/get_mic.c
@@ -50,7 +50,8 @@
   EVP_MD_CTX *md5;
   u_char hash[16];
   DES_key_schedule schedule;
-  EVP_CIPHER_CTX des_ctx;
+  gsskrb5_cipher_ctx des_ctx;
+  int cipher_error;
   DES_cblock deskey;
   DES_cblock zero;
   int32_t seq_number;
@@ -111,10 +112,19 @@
 	  (ctx->more_flags & LOCAL) ? 0 : 0xFF,
 	  4);
 
-  EVP_CIPHER_CTX_init(&des_ctx);
-  EVP_CipherInit_ex(&des_ctx, EVP_des_cbc(), NULL, key->keyvalue.data, p + 8, 1);
-  EVP_Cipher(&des_ctx, p, p, 8);
-  EVP_CIPHER_CTX_cleanup(&des_ctx);
+  cipher_error = gsskrb5_cipher_init(&des_ctx, EVP_des_cbc(), key->keyvalue.data, p + 8, 1);
+  if (!cipher_error) {
+    cipher_error = gsskrb5_cipher_update(&des_ctx, p, p, 8);
+    gsskrb5_cipher_free(&des_ctx);
+  }
+  if (cipher_error) {
+    HEIMDAL_MUTEX_unlock(&ctx->ctx_id_mutex);
+    memset_s(deskey, sizeof(deskey), 0, sizeof(deskey));
+    memset_s(&schedule, sizeof(schedule), 0, sizeof(schedule));
+    _gsskrb5_release_buffer(minor_status, message_token);
+    *minor_status = cipher_error;
+    return GSS_S_FAILURE;
+  }
 
   krb5_auth_con_setlocalseqnumber (context,
 			       ctx->auth_context,
