$NetBSD$

Backport OpenSSL 4 compatibility from upstream commit
https://github.com/krb5/krb5/commit/5e4e8452328804948d042235bbf58ca457795857
Adapt const propagation to the 1.22.2 certificate matcher without changing it.

--- plugins/tls/k5tls/openssl.c
+++ plugins/tls/k5tls/openssl.c
@@ -38,6 +38,24 @@
 #include <openssl/x509v3.h>
 #include <dirent.h>
 
+#if OPENSSL_VERSION_NUMBER < 0x10100000L
+/* Make X509_get_subject_name() accept a const pointer by adding a cast. */
+#define X509_get_subject_name(a) X509_get_subject_name((X509 *)a)
+
+/* OpenSSL 1.0 did not have TLS_client_method(); use the best alternative. */
+#define TLS_client_method() SSLv23_client_method()
+#endif
+
+#if OPENSSL_VERSION_NUMBER < 0x40000000L
+/*
+ * OpenSSL 4.0 constifies the result of X509_STORE_CTX_get_current_cert() and
+ * the input of X509_check_host() and X509_check_ip_asc().  For prior versions,
+ * make the latter two functions accept const pointers via a cast.
+ */
+#define X509_check_host(a, b, c, d, e) X509_check_host((X509 *)a, b, c, d, e)
+#define X509_check_ip_asc(a, b, c) X509_check_ip_asc((X509 *)a, b, c)
+#endif
+
 struct k5_tls_handle_st {
     SSL *ssl;
     char *servername;
@@ -51,9 +69,11 @@
 int
 init_openssl(void)
 {
+#if OPENSSL_VERSION_NUMBER < 0x10100000L
     SSL_library_init();
     SSL_load_error_strings();
     OpenSSL_add_all_algorithms();
+#endif
     ex_context_id = SSL_get_ex_new_index(0, NULL, NULL, NULL, NULL);
     ex_handle_id = SSL_get_ex_new_index(0, NULL, NULL, NULL, NULL);
     return 0;
@@ -139,10 +159,10 @@
 
 /* Fetch the list of subjectAltNames from a certificate. */
 static GENERAL_NAMES *
-get_cert_sans(X509 *x)
+get_cert_sans(const X509 *x)
 {
     int ext;
-    X509_EXTENSION *san_ext;
+    const X509_EXTENSION *san_ext;
 
     ext = X509_get_ext_by_NID(x, NID_subject_alt_name, -1);
     if (ext < 0)
@@ -156,9 +176,9 @@
 /* Fetch a CN value from the subjct name field, returning its length, or -1 if
  * there is no subject name or it contains no CN value. */
 static int
-get_cert_cn(X509 *x, char *buf, size_t bufsize)
-{
-    X509_NAME *name;
+get_cert_cn(const X509 *x, char *buf, size_t bufsize)
+{
+    const X509_NAME *name;
 
     name = X509_get_subject_name(x);
     if (name == NULL)
@@ -168,7 +188,7 @@
 
 /* Return true if text matches any of the addresses we can recover from x. */
 static krb5_boolean
-check_cert_address(X509 *x, const char *text)
+check_cert_address(const X509 *x, const char *text)
 {
     char buf[1024];
     GENERAL_NAMES *sans;
@@ -227,7 +247,7 @@
 
 /* Return true if expected matches any of the names we can recover from x. */
 static krb5_boolean
-check_cert_servername(X509 *x, const char *expected)
+check_cert_servername(const X509 *x, const char *expected)
 {
     char buf[1024];
     GENERAL_NAMES *sans;
@@ -272,7 +292,7 @@
 }
 
 static krb5_boolean
-check_cert_name_or_ip(X509 *x, const char *expected_name)
+check_cert_name_or_ip(const X509 *x, const char *expected_name)
 {
     struct in_addr in;
     struct in6_addr in6;
@@ -288,7 +308,7 @@
 static int
 verify_callback(int preverify_ok, X509_STORE_CTX *store_ctx)
 {
-    X509 *x;
+    const X509 *x;
     SSL *ssl;
     BIO *bio;
     krb5_context context;
@@ -445,7 +465,7 @@
         return KRB5_PLUGIN_OP_NOTSUPP;
 
     /* Do general SSL library setup. */
-    ctx = SSL_CTX_new(SSLv23_client_method());
+    ctx = SSL_CTX_new(TLS_client_method());
     if (ctx == NULL)
         goto error;
 
