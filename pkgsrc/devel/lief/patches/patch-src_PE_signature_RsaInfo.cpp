$NetBSD$

Copied RSA contexts already contain all components in Mbed TLS 4.2.

--- src/PE/signature/RsaInfo.cpp.orig
+++ src/PE/signature/RsaInfo.cpp
@@ -37,7 +37,6 @@
   mbedtls_rsa_set_padding(local_ctx, pctx->private_padding,
                           static_cast<mbedtls_md_type_t>(pctx->private_hash_id));
   mbedtls_rsa_copy(local_ctx, pctx);
-  mbedtls_rsa_complete(local_ctx);
   ctx_ = reinterpret_cast<RsaInfo::rsa_ctx_handle>(local_ctx);
 }
 
@@ -49,7 +48,6 @@
     mbedtls_rsa_set_padding(local_ctx, octx->private_padding,
                             static_cast<mbedtls_md_type_t>(octx->private_hash_id));
     mbedtls_rsa_copy(local_ctx, octx);
-    mbedtls_rsa_complete(local_ctx);
     ctx_ = reinterpret_cast<RsaInfo::rsa_ctx_handle>(local_ctx);
   }
 }
