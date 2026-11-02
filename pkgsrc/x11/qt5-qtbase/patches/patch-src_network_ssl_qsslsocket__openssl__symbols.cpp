$NetBSD$

Build with OpenSSL 4, which adds const to the X.509 API and makes
ASN1_STRING opaque. Based on Qt 6 commit e806630e694d (QTBUG-145221).

--- src/network/ssl/qsslsocket_openssl_symbols.cpp.orig
+++ src/network/ssl/qsslsocket_openssl_symbols.cpp
@@ -138,6 +138,7 @@
 #endif // QT_LINKED_OPENSSL
 
 DEFINEFUNC(const unsigned char *, ASN1_STRING_get0_data, const ASN1_STRING *a, a, return nullptr, return)
+DEFINEFUNC(int, ASN1_STRING_type, const ASN1_STRING *a, a, return 0, return)
 DEFINEFUNC2(int, OPENSSL_init_ssl, uint64_t opts, opts, const OPENSSL_INIT_SETTINGS *settings, settings, return 0, return)
 DEFINEFUNC2(int, OPENSSL_init_crypto, uint64_t opts, opts, const OPENSSL_INIT_SETTINGS *settings, settings, return 0, return)
 DEFINEFUNC(BIO *, BIO_new, const BIO_METHOD *a, a, return nullptr, return)
@@ -244,8 +245,8 @@
 
 DEFINEFUNC(long, ASN1_INTEGER_get, ASN1_INTEGER *a, a, return 0, return)
 DEFINEFUNC2(int, ASN1_INTEGER_cmp, const ASN1_INTEGER *a, a, const ASN1_INTEGER *b, b, return 1, return)
-DEFINEFUNC(int, ASN1_STRING_length, ASN1_STRING *a, a, return 0, return)
-DEFINEFUNC2(int, ASN1_STRING_to_UTF8, unsigned char **a, a, ASN1_STRING *b, b, return 0, return)
+DEFINEFUNC(int, ASN1_STRING_length, const ASN1_STRING *a, a, return 0, return)
+DEFINEFUNC2(int, ASN1_STRING_to_UTF8, unsigned char **a, a, const ASN1_STRING *b, b, return 0, return)
 DEFINEFUNC4(long, BIO_ctrl, BIO *a, a, int b, b, long c, c, void *d, d, return -1, return)
 DEFINEFUNC(int, BIO_free, BIO *a, a, return 0, return)
 DEFINEFUNC2(BIO *, BIO_new_mem_buf, void *a, a, int b, b, return nullptr, return)
@@ -309,7 +310,7 @@
 DEFINEFUNC(int, OBJ_sn2nid, const char *s, s, return 0, return)
 DEFINEFUNC(int, OBJ_ln2nid, const char *s, s, return 0, return)
 DEFINEFUNC3(int, i2t_ASN1_OBJECT, char *a, a, int b, b, ASN1_OBJECT *c, c, return -1, return)
-DEFINEFUNC4(int, OBJ_obj2txt, char *a, a, int b, b, ASN1_OBJECT *c, c, int d, d, return -1, return)
+DEFINEFUNC4(int, OBJ_obj2txt, char *a, a, int b, b, const ASN1_OBJECT *c, c, int d, d, return -1, return)
 DEFINEFUNC(int, OBJ_obj2nid, const ASN1_OBJECT *a, a, return NID_undef, return)
 DEFINEFUNC4(EVP_PKEY *, PEM_read_bio_PrivateKey, BIO *a, a, EVP_PKEY **b, b, pem_password_cb *c, c, void *d, d, return nullptr, return)
 DEFINEFUNC4(DSA *, PEM_read_bio_DSAPrivateKey, BIO *a, a, DSA **b, b, pem_password_cb *c, c, void *d, d, return nullptr, return)
@@ -408,31 +409,31 @@
 DEFINEFUNC4(int, X509_digest, const X509 *x509, x509, const EVP_MD *type, type, unsigned char *md, md, unsigned int *len, len, return -1, return)
 DEFINEFUNC(X509 *, X509_dup, X509 *a, a, return nullptr, return)
 DEFINEFUNC2(void, X509_print, BIO *a, a, X509 *b, b, return, DUMMYARG);
-DEFINEFUNC(ASN1_OBJECT *, X509_EXTENSION_get_object, X509_EXTENSION *a, a, return nullptr, return)
+DEFINEFUNC(QT_OPENSSL4_CONST ASN1_OBJECT *, X509_EXTENSION_get_object, QT_OPENSSL4_CONST X509_EXTENSION *a, a, return nullptr, return)
 DEFINEFUNC(void, X509_free, X509 *a, a, return, DUMMYARG)
 //Q_AUTOTEST_EXPORT ASN1_TIME *q_X509_gmtime_adj(ASN1_TIME *s, long adj);
 DEFINEFUNC2(ASN1_TIME *, X509_gmtime_adj, ASN1_TIME *s, s, long adj, adj, return nullptr, return)
 DEFINEFUNC(void, ASN1_TIME_free, ASN1_TIME *t, t, return, DUMMYARG)
-DEFINEFUNC2(X509_EXTENSION *, X509_get_ext, X509 *a, a, int b, b, return nullptr, return)
+DEFINEFUNC2(QT_OPENSSL4_CONST X509_EXTENSION *, X509_get_ext, X509 *a, a, int b, b, return nullptr, return)
 DEFINEFUNC(int, X509_get_ext_count, X509 *a, a, return 0, return)
 DEFINEFUNC4(void *, X509_get_ext_d2i, X509 *a, a, int b, b, int *c, c, int *d, d, return nullptr, return)
-DEFINEFUNC(const X509V3_EXT_METHOD *, X509V3_EXT_get, X509_EXTENSION *a, a, return nullptr, return)
-DEFINEFUNC(void *, X509V3_EXT_d2i, X509_EXTENSION *a, a, return nullptr, return)
-DEFINEFUNC(int, X509_EXTENSION_get_critical, X509_EXTENSION *a, a, return 0, return)
-DEFINEFUNC(ASN1_OCTET_STRING *, X509_EXTENSION_get_data, X509_EXTENSION *a, a, return nullptr, return)
+DEFINEFUNC(const X509V3_EXT_METHOD *, X509V3_EXT_get, QT_OPENSSL4_CONST X509_EXTENSION *a, a, return nullptr, return)
+DEFINEFUNC(void *, X509V3_EXT_d2i, QT_OPENSSL4_CONST X509_EXTENSION *a, a, return nullptr, return)
+DEFINEFUNC(int, X509_EXTENSION_get_critical, const X509_EXTENSION *a, a, return 0, return)
+DEFINEFUNC(QT_OPENSSL4_CONST ASN1_OCTET_STRING *, X509_EXTENSION_get_data, QT_OPENSSL4_CONST X509_EXTENSION *a, a, return nullptr, return)
 DEFINEFUNC(void, BASIC_CONSTRAINTS_free, BASIC_CONSTRAINTS *a, a, return, DUMMYARG)
 DEFINEFUNC(void, AUTHORITY_KEYID_free, AUTHORITY_KEYID *a, a, return, DUMMYARG)
 DEFINEFUNC(void, GENERAL_NAME_free, GENERAL_NAME *a, a, return, DUMMYARG)
 DEFINEFUNC2(int, ASN1_STRING_print, BIO *a, a, const ASN1_STRING *b, b, return 0, return)
 DEFINEFUNC2(int, X509_check_issued, X509 *a, a, X509 *b, b, return -1, return)
-DEFINEFUNC(X509_NAME *, X509_get_issuer_name, X509 *a, a, return nullptr, return)
-DEFINEFUNC(X509_NAME *, X509_get_subject_name, X509 *a, a, return nullptr, return)
+DEFINEFUNC(QT_OPENSSL4_CONST X509_NAME *, X509_get_issuer_name, X509 *a, a, return nullptr, return)
+DEFINEFUNC(QT_OPENSSL4_CONST X509_NAME *, X509_get_subject_name, X509 *a, a, return nullptr, return)
 DEFINEFUNC(ASN1_INTEGER *, X509_get_serialNumber, X509 *a, a, return nullptr, return)
 DEFINEFUNC(int, X509_verify_cert, X509_STORE_CTX *a, a, return -1, return)
-DEFINEFUNC(int, X509_NAME_entry_count, X509_NAME *a, a, return 0, return)
-DEFINEFUNC2(X509_NAME_ENTRY *, X509_NAME_get_entry, X509_NAME *a, a, int b, b, return nullptr, return)
-DEFINEFUNC(ASN1_STRING *, X509_NAME_ENTRY_get_data, X509_NAME_ENTRY *a, a, return nullptr, return)
-DEFINEFUNC(ASN1_OBJECT *, X509_NAME_ENTRY_get_object, X509_NAME_ENTRY *a, a, return nullptr, return)
+DEFINEFUNC(int, X509_NAME_entry_count, const X509_NAME *a, a, return 0, return)
+DEFINEFUNC2(QT_OPENSSL4_CONST X509_NAME_ENTRY *, X509_NAME_get_entry, const X509_NAME *a, a, int b, b, return nullptr, return)
+DEFINEFUNC(QT_OPENSSL4_CONST ASN1_STRING *, X509_NAME_ENTRY_get_data, const X509_NAME_ENTRY *a, a, return nullptr, return)
+DEFINEFUNC(QT_OPENSSL4_CONST ASN1_OBJECT *, X509_NAME_ENTRY_get_object, const X509_NAME_ENTRY *a, a, return nullptr, return)
 DEFINEFUNC(EVP_PKEY *, X509_PUBKEY_get, X509_PUBKEY *a, a, return nullptr, return)
 DEFINEFUNC(void, X509_STORE_free, X509_STORE *a, a, return, DUMMYARG)
 DEFINEFUNC(X509_STORE *, X509_STORE_new, DUMMYARG, DUMMYARG, return nullptr, return)
@@ -869,6 +870,7 @@
     RESOLVEFUNC(OPENSSL_init_ssl)
     RESOLVEFUNC(OPENSSL_init_crypto)
     RESOLVEFUNC(ASN1_STRING_get0_data)
+    RESOLVEFUNC(ASN1_STRING_type)
     RESOLVEFUNC(EVP_CIPHER_CTX_reset)
     RESOLVEFUNC(AUTHORITY_INFO_ACCESS_free)
     RESOLVEFUNC(EVP_PKEY_up_ref)
@@ -1258,13 +1260,13 @@
 //==============================================================================
 QDateTime q_getTimeFromASN1(const ASN1_TIME *aTime)
 {
-    size_t lTimeLength = aTime->length;
-    char *pString = (char *) aTime->data;
+    size_t lTimeLength = q_ASN1_STRING_length(aTime);
+    const char *pString = reinterpret_cast<const char *>(q_ASN1_STRING_get0_data(aTime));
     auto isValidPointer = [pString, lTimeLength](const char *const probe){
         return size_t(probe - pString) < lTimeLength;
     };
 
-    if (aTime->type == V_ASN1_UTCTIME) {
+    if (q_ASN1_STRING_type(aTime) == V_ASN1_UTCTIME) {
 
         char lBuffer[24];
         char *pBuffer = lBuffer;
@@ -1337,7 +1339,7 @@
         result = result.addSecs(lSecondsFromUCT);
         return result;
 
-    } else if (aTime->type == V_ASN1_GENERALIZEDTIME) {
+    } else if (q_ASN1_STRING_type(aTime) == V_ASN1_GENERALIZEDTIME) {
 
         if (lTimeLength < 15)
             return QDateTime(); // hopefully never triggered
