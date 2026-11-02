$NetBSD$

Build with OpenSSL 4, which adds const to the X.509 API and makes
ASN1_STRING opaque. Based on Qt 6 commit e806630e694d (QTBUG-145221).

--- src/network/ssl/qsslcertificate_p.h.orig
+++ src/network/ssl/qsslcertificate_p.h
@@ -64,6 +64,15 @@
 
 #ifndef QT_NO_OPENSSL
 #include <openssl/x509.h>
+
+// OpenSSL 4 adds const to the X.509 API and makes ASN1_STRING opaque.
+#ifndef QT_OPENSSL4_CONST
+#if defined(OPENSSL_VERSION_MAJOR) && OPENSSL_VERSION_MAJOR >= 4
+#define QT_OPENSSL4_CONST const
+#else
+#define QT_OPENSSL4_CONST
+#endif
+#endif
 #else
 struct X509;
 struct X509_EXTENSION;
@@ -131,15 +140,15 @@
 
     void init(const QByteArray &data, QSsl::EncodingFormat format);
 
-    static QByteArray asn1ObjectId(ASN1_OBJECT *object);
-    static QByteArray asn1ObjectName(ASN1_OBJECT *object);
+    static QByteArray asn1ObjectId(const ASN1_OBJECT *object);
+    static QByteArray asn1ObjectName(const ASN1_OBJECT *object);
     static QByteArray QByteArray_from_X509(X509 *x509, QSsl::EncodingFormat format);
     static QString text_from_X509(X509 *x509);
     static QSslCertificate QSslCertificate_from_X509(X509 *x509);
     static QList<QSslCertificate> certificatesFromPem(const QByteArray &pem, int count = -1);
     static QList<QSslCertificate> certificatesFromDer(const QByteArray &der, int count = -1);
     static bool isBlacklisted(const QSslCertificate &certificate);
-    static QSslCertificateExtension convertExtension(X509_EXTENSION *ext);
+    static QSslCertificateExtension convertExtension(QT_OPENSSL4_CONST X509_EXTENSION *ext);
     static QByteArray subjectInfoToString(QSslCertificate::SubjectInfo info);
 
     friend class QSslSocketBackendPrivate;
