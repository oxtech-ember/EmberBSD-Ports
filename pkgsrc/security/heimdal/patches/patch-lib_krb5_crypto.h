$NetBSD$

Use opaque OpenSSL contexts in the native NetBSD backend while preserving
keyed schedule state and explicit failure cleanup.
Origin: NetBSD crypto/external/bsd/heimdal with EmberBSD lifecycle corrections.

--- lib/krb5/crypto.h
+++ lib/krb5/crypto.h
@@ -195,7 +195,25 @@
      * Normally we'd say EVP_CIPHER_CTX here, but!  this header gets
      * included in lib/krb5/pkinit-ec.ck
      */
+#if defined(EMBERBSD_BASE_HEIMDAL) && defined(HAVE_HCRYPTO_W_OPENSSL) && \
+    defined(OPENSSL_VERSION_NUMBER) && OPENSSL_VERSION_NUMBER >= 0x10100000L && \
+    !defined(LIBRESSL_VERSION_NUMBER)
+#define HEIMDAL_OPAQUE_EVP 1
+    EVP_CIPHER_CTX *ectx;
+    EVP_CIPHER_CTX *dctx;
+    krb5_error_code error;
+#else
     EVP_CIPHER_CTX ectx;
     EVP_CIPHER_CTX dctx;
-};
-#endif
+#endif
+};
+#ifdef HEIMDAL_OPAQUE_EVP
+#define HEIM_EVP_SCHEDULE_CTX(s, field) ((s)->field)
+#define HEIM_EVP_SCHEDULE_ERROR(s, context) ((s)->error)
+#define HEIM_EVP_TRY(expr) do { if ((expr) <= 0) return EINVAL; } while (0)
+#else
+#define HEIM_EVP_SCHEDULE_CTX(s, field) (&(s)->field)
+#define HEIM_EVP_SCHEDULE_ERROR(s, context) krb5_enomem(context)
+#define HEIM_EVP_TRY(expr) ((void)(expr))
+#endif
+#endif
