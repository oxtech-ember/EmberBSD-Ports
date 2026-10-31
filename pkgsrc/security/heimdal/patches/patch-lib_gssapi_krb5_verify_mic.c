$NetBSD$

Support opaque OpenSSL contexts in the native Heimdal GSS backend.
Origin: NetBSD Heimdal adaptation; EmberBSD lifecycle and error handling.

--- lib/gssapi/krb5/verify_mic.c
+++ lib/gssapi/krb5/verify_mic.c
@@ -51,7 +51,8 @@
   EVP_MD_CTX *md5;
   u_char hash[16], *seq;
   DES_key_schedule schedule;
-  EVP_CIPHER_CTX des_ctx;
+  gsskrb5_cipher_ctx des_ctx;
+  int cipher_error;
   DES_cblock zero;
   DES_cblock deskey;
   uint32_t seq_number;
@@ -100,10 +101,18 @@
 
   p -= 16;
 
-  EVP_CIPHER_CTX_init(&des_ctx);
-  EVP_CipherInit_ex(&des_ctx, EVP_des_cbc(), NULL, key->keyvalue.data, hash, 0);
-  EVP_Cipher(&des_ctx, p, p, 8);
-  EVP_CIPHER_CTX_cleanup(&des_ctx);
+  cipher_error = gsskrb5_cipher_init(&des_ctx, EVP_des_cbc(), key->keyvalue.data, hash, 0);
+  if (!cipher_error) {
+    cipher_error = gsskrb5_cipher_update(&des_ctx, p, p, 8);
+    gsskrb5_cipher_free(&des_ctx);
+  }
+  if (cipher_error) {
+    HEIMDAL_MUTEX_unlock(&context_handle->ctx_id_mutex);
+    memset_s(deskey, sizeof(deskey), 0, sizeof(deskey));
+    memset_s(&schedule, sizeof(schedule), 0, sizeof(schedule));
+    *minor_status = cipher_error;
+    return GSS_S_FAILURE;
+  }
 
   memset_s(deskey, sizeof(deskey), 0, sizeof(deskey));
   memset_s(&schedule, sizeof(schedule), 0, sizeof(schedule));
