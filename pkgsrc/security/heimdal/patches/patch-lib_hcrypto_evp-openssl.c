Respect OpenSSL 3 provider availability and existing hcrypto fallback.

--- lib/hcrypto/evp-openssl.c.orig
+++ lib/hcrypto/evp-openssl.c
@@ -74,6 +74,65 @@
 
 /* Now it's safe to include OpenSSL headers */
 #include <openssl/evp.h>
+#include <openssl/err.h>
+#include <openssl/objects.h>
+
+/* OpenSSL 3 legacy descriptors need not have a loaded implementation.
+ * Check the current provider selection on every lookup, not in the once cache.
+ */
+#if OPENSSL_VERSION_NUMBER >= 0x30500000L && !defined(LIBRESSL_VERSION_NUMBER)
+static int
+ossl_algorithm_available(int nid, int digest)
+{
+    const char *name = OBJ_nid2sn(nid);
+    EVP_CIPHER *cipher = NULL;
+    EVP_MD *md = NULL;
+    unsigned long error;
+    char *properties;
+    int mark, fallback = 0, count;
+
+    if (name == NULL)
+        return -1;
+    mark = ERR_set_mark();
+    if (digest)
+        md = EVP_MD_fetch(NULL, name, NULL);
+    else
+        cipher = EVP_CIPHER_fetch(NULL, name, NULL);
+    if (md != NULL || cipher != NULL) {
+        EVP_MD_free(md);
+        EVP_CIPHER_free(cipher);
+        if (mark)
+            ERR_clear_last_mark();
+        return 1;
+    }
+    count = ERR_count_to_mark();
+    error = ERR_peek_last_error();
+#if HCRYPTO_FALLBACK
+    if (count == 1 && ERR_GET_LIB(error) == ERR_LIB_EVP &&
+        ERR_GET_REASON(error) == ERR_R_UNSUPPORTED) {
+        properties = EVP_get1_default_properties(NULL);
+        if (properties != NULL) {
+            fallback = properties[0] == '\0' && ERR_count_to_mark() == 1;
+            OPENSSL_free(properties);
+        }
+    }
+#else
+    (void)count;
+    (void)error;
+    (void)properties;
+#endif
+    if (fallback) {
+        if (mark)
+            ERR_pop_to_mark();
+        else
+            ERR_clear_error();
+        return 0;
+    }
+    if (mark)
+        ERR_clear_last_mark();
+    return -1;
+}
+#endif
 
 #if OPENSSL_VERSION_NUMBER < 0x10100000L || defined(LIBRESSL_VERSION_NUMBER)
 #define EVP_MD_CTX_new EVP_MD_CTX_create
@@ -249,6 +308,11 @@
                unsigned long flags, int nid)
 {
     struct once_init_cipher_ctx arg;
+#if OPENSSL_VERSION_NUMBER >= 0x30500000L && !defined(LIBRESSL_VERSION_NUMBER)
+    int available = ossl_algorithm_available(nid, 0);
+    if (available <= 0)
+        return available == 0 ? fallback : NULL;
+#endif
 
     arg.flags = flags;
     arg.hc_memoizep = hc_memoizep;
@@ -256,6 +320,10 @@
     arg.fallback = fallback;
     arg.nid = nid;
     heim_base_once_f(once, &arg, get_EVP_CIPHER_once_cb);
+#if OPENSSL_VERSION_NUMBER >= 0x30500000L && !defined(LIBRESSL_VERSION_NUMBER)
+    if (fallback != NULL && *hc_memoizep == fallback)
+        return NULL; /* A fetched provider had no matching legacy descriptor. */
+#endif
     return *hc_memoizep; /* May be NULL */
 }
 
@@ -374,6 +442,11 @@
            hc_evp_md_init md_init, int nid)
 {
     struct once_init_md_ctx ctx;
+#if OPENSSL_VERSION_NUMBER >= 0x30500000L && !defined(LIBRESSL_VERSION_NUMBER)
+    int available = ossl_algorithm_available(nid, 1);
+    if (available <= 0)
+        return available == 0 ? fallback : NULL;
+#endif
 
     ctx.ossl_memoizep = ossl_memoizep;
     ctx.hc_memoizep = hc_memoizep;
@@ -382,6 +455,10 @@
     ctx.md_init = md_init;
     ctx.nid = nid;
     heim_base_once_f(once, &ctx, get_EVP_MD_once_cb);
+#if OPENSSL_VERSION_NUMBER >= 0x30500000L && !defined(LIBRESSL_VERSION_NUMBER)
+    if (fallback != NULL && *hc_memoizep == fallback)
+        return NULL; /* A fetched provider had no matching legacy descriptor. */
+#endif
     return *hc_memoizep; /* May be NULL */
 }
 
