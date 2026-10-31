$NetBSD$

Support opaque OpenSSL contexts in the native Heimdal GSS backend.
Origin: NetBSD Heimdal adaptation; EmberBSD lifecycle and error handling.

--- lib/gssapi/krb5/wrap.c
+++ lib/gssapi/krb5/wrap.c
@@ -212,7 +212,8 @@
   EVP_MD_CTX *md5;
   u_char hash[16];
   DES_key_schedule schedule;
-  EVP_CIPHER_CTX des_ctx;
+  gsskrb5_cipher_ctx des_ctx;
+  int cipher_error;
   DES_cblock deskey;
   DES_cblock zero;
   size_t i;
@@ -299,15 +300,24 @@
 	  (ctx->more_flags & LOCAL) ? 0 : 0xFF,
 	  4);
 
-  EVP_CIPHER_CTX_init(&des_ctx);
-  EVP_CipherInit_ex(&des_ctx, EVP_des_cbc(), NULL, key->keyvalue.data, p + 8, 1);
-  EVP_Cipher(&des_ctx, p, p, 8);
-  EVP_CIPHER_CTX_cleanup(&des_ctx);
-
-  krb5_auth_con_setlocalseqnumber (context,
-			       ctx->auth_context,
-			       ++seq_number);
+  cipher_error = gsskrb5_cipher_init(&des_ctx, EVP_des_cbc(), key->keyvalue.data, p + 8, 1);
+  if (!cipher_error) {
+    cipher_error = gsskrb5_cipher_update(&des_ctx, p, p, 8);
+    gsskrb5_cipher_free(&des_ctx);
+  }
+  if (cipher_error) {
+    HEIMDAL_MUTEX_unlock(&ctx->ctx_id_mutex);
+    memset_s(deskey, sizeof(deskey), 0, sizeof(deskey));
+    memset_s(&schedule, sizeof(schedule), 0, sizeof(schedule));
+    _gsskrb5_release_buffer(minor_status, output_message_buffer);
+    *minor_status = cipher_error;
+    return GSS_S_FAILURE;
+  }
+
+#ifndef GSSKRB5_OPAQUE_CIPHER
+  krb5_auth_con_setlocalseqnumber(context, ctx->auth_context, ++seq_number);
   HEIMDAL_MUTEX_unlock(&ctx->ctx_id_mutex);
+#endif
 
   /* encrypt the data */
   p += 16;
@@ -318,14 +328,28 @@
       for (i = 0; i < sizeof(deskey); ++i)
 	  deskey[i] ^= 0xf0;
 
-      EVP_CIPHER_CTX_init(&des_ctx);
-      EVP_CipherInit_ex(&des_ctx, EVP_des_cbc(), NULL, deskey, zero, 1);
-      EVP_Cipher(&des_ctx, p, p, datalen);
-      EVP_CIPHER_CTX_cleanup(&des_ctx);
+      cipher_error = gsskrb5_cipher_init(&des_ctx, EVP_des_cbc(), deskey, zero, 1);
+      if (!cipher_error) {
+        cipher_error = gsskrb5_cipher_update(&des_ctx, p, p, datalen);
+        gsskrb5_cipher_free(&des_ctx);
+      }
+      if (cipher_error) {
+        HEIMDAL_MUTEX_unlock(&ctx->ctx_id_mutex);
+        memset_s(deskey, sizeof(deskey), 0, sizeof(deskey));
+        memset_s(&schedule, sizeof(schedule), 0, sizeof(schedule));
+        _gsskrb5_release_buffer(minor_status, output_message_buffer);
+        *minor_status = cipher_error;
+        return GSS_S_FAILURE;
+      }
   }
   memset (deskey, 0, sizeof(deskey));
   memset (&schedule, 0, sizeof(schedule));
 
+#ifdef GSSKRB5_OPAQUE_CIPHER
+  krb5_auth_con_setlocalseqnumber(context, ctx->auth_context, ++seq_number);
+  HEIMDAL_MUTEX_unlock(&ctx->ctx_id_mutex);
+#endif
+
   if(conf_state != NULL)
       *conf_state = conf_req_flag;
   *minor_status = 0;
