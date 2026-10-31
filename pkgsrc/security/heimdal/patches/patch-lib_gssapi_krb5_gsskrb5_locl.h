$NetBSD$

Support opaque OpenSSL contexts in the native Heimdal GSS backend.
Origin: NetBSD Heimdal adaptation; EmberBSD lifecycle and error handling.

--- lib/gssapi/krb5/gsskrb5_locl.h
+++ lib/gssapi/krb5/gsskrb5_locl.h
@@ -134,4 +134,77 @@
 #define SC_LOCAL_SUBKEY	  0x08
 #define SC_REMOTE_SUBKEY  0x10
 
+/* The base backend uses OpenSSL directly; portable hcrypto keeps its
+ * non-opaque context and historical call semantics. */
+#if defined(EMBERBSD_BASE_HEIMDAL) && defined(HAVE_HCRYPTO_W_OPENSSL) && \
+    OPENSSL_VERSION_NUMBER >= 0x10100000L && !defined(LIBRESSL_VERSION_NUMBER)
+#define GSSKRB5_OPAQUE_CIPHER 1
+#endif
+
+typedef struct gsskrb5_cipher_ctx {
+#ifdef GSSKRB5_OPAQUE_CIPHER
+    EVP_CIPHER_CTX *ctx;
+#else
+    EVP_CIPHER_CTX storage;
+    EVP_CIPHER_CTX *ctx;
+#endif
+} gsskrb5_cipher_ctx;
+
+static inline int
+gsskrb5_cipher_init(gsskrb5_cipher_ctx *c, const EVP_CIPHER *cipher,
+                    const void *key, const unsigned char *iv, int enc)
+{
+#ifdef GSSKRB5_OPAQUE_CIPHER
+    c->ctx = EVP_CIPHER_CTX_new();
+    if (c->ctx == NULL)
+        return ENOMEM;
+    if (EVP_CipherInit_ex(c->ctx, cipher, NULL, key, iv, enc) != 1) {
+        EVP_CIPHER_CTX_free(c->ctx);
+        c->ctx = NULL;
+        return EINVAL;
+    }
+#else
+    c->ctx = &c->storage;
+    EVP_CIPHER_CTX_init(c->ctx);
+    EVP_CipherInit_ex(c->ctx, cipher, NULL, key, iv, enc);
+#endif
+    return 0;
+}
+
+static inline int
+gsskrb5_cipher_update(gsskrb5_cipher_ctx *c, void *out, const void *in, size_t len)
+{
+#ifdef GSSKRB5_OPAQUE_CIPHER
+    if (len != 0 && EVP_Cipher(c->ctx, out, in, len) <= 0)
+        return EINVAL;
+#else
+    EVP_Cipher(c->ctx, out, in, len);
+#endif
+    return 0;
+}
+
+static inline void
+gsskrb5_cipher_free(gsskrb5_cipher_ctx *c)
+{
+#ifdef GSSKRB5_OPAQUE_CIPHER
+    EVP_CIPHER_CTX_free(c->ctx);
+#else
+    EVP_CIPHER_CTX_cleanup(c->ctx);
+#endif
+}
+
+static inline int
+gsskrb5_cipher_once(const EVP_CIPHER *cipher, const void *key,
+                    const unsigned char *iv, int enc, void *out,
+                    const void *in, size_t len)
+{
+    gsskrb5_cipher_ctx c;
+    int ret = gsskrb5_cipher_init(&c, cipher, key, iv, enc);
+    if (ret)
+        return ret;
+    ret = gsskrb5_cipher_update(&c, out, in, len);
+    gsskrb5_cipher_free(&c);
+    return ret;
+}
+
 #endif
