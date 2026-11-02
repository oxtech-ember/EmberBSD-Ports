$NetBSD$

Build with OpenSSL 4, which adds const to the X.509 API and makes
ASN1_STRING opaque. Based on Qt 6 commit e806630e694d (QTBUG-145221).

--- src/network/ssl/qsslsocket_openssl_symbols_p.h.orig
+++ src/network/ssl/qsslsocket_openssl_symbols_p.h
@@ -226,6 +226,7 @@
 // depending on the functionality.
 
 const unsigned char * q_ASN1_STRING_get0_data(const ASN1_STRING *x);
+int q_ASN1_STRING_type(const ASN1_STRING *x);
 
 Q_AUTOTEST_EXPORT BIO *q_BIO_new(const BIO_METHOD *a);
 Q_AUTOTEST_EXPORT const BIO_METHOD *q_BIO_s_mem();
@@ -373,8 +374,8 @@
 bool q_resolveOpenSslSymbols();
 long q_ASN1_INTEGER_get(ASN1_INTEGER *a);
 int q_ASN1_INTEGER_cmp(const ASN1_INTEGER *x, const ASN1_INTEGER *y);
-int q_ASN1_STRING_length(ASN1_STRING *a);
-int q_ASN1_STRING_to_UTF8(unsigned char **a, ASN1_STRING *b);
+int q_ASN1_STRING_length(const ASN1_STRING *a);
+int q_ASN1_STRING_to_UTF8(unsigned char **a, const ASN1_STRING *b);
 long q_BIO_ctrl(BIO *a, int b, long c, void *d);
 Q_AUTOTEST_EXPORT int q_BIO_free(BIO *a);
 BIO *q_BIO_new_mem_buf(void *a, int b);
@@ -457,7 +458,7 @@
 int q_OBJ_sn2nid(const char *s);
 int q_OBJ_ln2nid(const char *s);
 int q_i2t_ASN1_OBJECT(char *buf, int buf_len, ASN1_OBJECT *obj);
-int q_OBJ_obj2txt(char *buf, int buf_len, ASN1_OBJECT *obj, int no_name);
+int q_OBJ_obj2txt(char *buf, int buf_len, const ASN1_OBJECT *obj, int no_name);
 int q_OBJ_obj2nid(const ASN1_OBJECT *a);
 #define q_EVP_get_digestbynid(a) q_EVP_get_digestbyname(q_OBJ_nid2sn(a))
 Q_AUTOTEST_EXPORT EVP_PKEY *q_PEM_read_bio_PrivateKey(BIO *a, EVP_PKEY **b, pem_password_cb *c, void *d);
@@ -556,29 +557,29 @@
 X509 *q_X509_dup(X509 *a);
 void q_X509_print(BIO *a, X509*b);
 int q_X509_digest(const X509 *x509, const EVP_MD *type, unsigned char *md, unsigned int *len);
-ASN1_OBJECT *q_X509_EXTENSION_get_object(X509_EXTENSION *a);
+QT_OPENSSL4_CONST ASN1_OBJECT *q_X509_EXTENSION_get_object(QT_OPENSSL4_CONST X509_EXTENSION *a);
 Q_AUTOTEST_EXPORT void q_X509_free(X509 *a);
 Q_AUTOTEST_EXPORT ASN1_TIME *q_X509_gmtime_adj(ASN1_TIME *s, long adj);
 Q_AUTOTEST_EXPORT void q_ASN1_TIME_free(ASN1_TIME *t);
-X509_EXTENSION *q_X509_get_ext(X509 *a, int b);
+QT_OPENSSL4_CONST X509_EXTENSION *q_X509_get_ext(X509 *a, int b);
 int q_X509_get_ext_count(X509 *a);
 void *q_X509_get_ext_d2i(X509 *a, int b, int *c, int *d);
-const X509V3_EXT_METHOD *q_X509V3_EXT_get(X509_EXTENSION *a);
-void *q_X509V3_EXT_d2i(X509_EXTENSION *a);
-int q_X509_EXTENSION_get_critical(X509_EXTENSION *a);
-ASN1_OCTET_STRING *q_X509_EXTENSION_get_data(X509_EXTENSION *a);
+const X509V3_EXT_METHOD *q_X509V3_EXT_get(QT_OPENSSL4_CONST X509_EXTENSION *a);
+void *q_X509V3_EXT_d2i(QT_OPENSSL4_CONST X509_EXTENSION *a);
+int q_X509_EXTENSION_get_critical(const X509_EXTENSION *a);
+QT_OPENSSL4_CONST ASN1_OCTET_STRING *q_X509_EXTENSION_get_data(QT_OPENSSL4_CONST X509_EXTENSION *a);
 void q_BASIC_CONSTRAINTS_free(BASIC_CONSTRAINTS *a);
 void q_AUTHORITY_KEYID_free(AUTHORITY_KEYID *a);
 int q_ASN1_STRING_print(BIO *a, const ASN1_STRING *b);
 int q_X509_check_issued(X509 *a, X509 *b);
-X509_NAME *q_X509_get_issuer_name(X509 *a);
-X509_NAME *q_X509_get_subject_name(X509 *a);
+QT_OPENSSL4_CONST X509_NAME *q_X509_get_issuer_name(X509 *a);
+QT_OPENSSL4_CONST X509_NAME *q_X509_get_subject_name(X509 *a);
 ASN1_INTEGER *q_X509_get_serialNumber(X509 *a);
 int q_X509_verify_cert(X509_STORE_CTX *ctx);
-int q_X509_NAME_entry_count(X509_NAME *a);
-X509_NAME_ENTRY *q_X509_NAME_get_entry(X509_NAME *a,int b);
-ASN1_STRING *q_X509_NAME_ENTRY_get_data(X509_NAME_ENTRY *a);
-ASN1_OBJECT *q_X509_NAME_ENTRY_get_object(X509_NAME_ENTRY *a);
+int q_X509_NAME_entry_count(const X509_NAME *a);
+QT_OPENSSL4_CONST X509_NAME_ENTRY *q_X509_NAME_get_entry(const X509_NAME *a,int b);
+QT_OPENSSL4_CONST ASN1_STRING *q_X509_NAME_ENTRY_get_data(const X509_NAME_ENTRY *a);
+QT_OPENSSL4_CONST ASN1_OBJECT *q_X509_NAME_ENTRY_get_object(const X509_NAME_ENTRY *a);
 EVP_PKEY *q_X509_PUBKEY_get(X509_PUBKEY *a);
 void q_X509_STORE_free(X509_STORE *store);
 X509_STORE *q_X509_STORE_new();
