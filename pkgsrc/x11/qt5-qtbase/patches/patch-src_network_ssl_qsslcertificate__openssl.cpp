$NetBSD$

Build with OpenSSL 4, which adds const to the X.509 API and makes
ASN1_STRING opaque. Based on Qt 6 commit e806630e694d (QTBUG-145221).

--- src/network/ssl/qsslcertificate_openssl.cpp.orig
+++ src/network/ssl/qsslcertificate_openssl.cpp
@@ -60,7 +60,7 @@
 }
 
 // forward declaration
-static QMultiMap<QByteArray, QString> _q_mapFromX509Name(X509_NAME *name);
+static QMultiMap<QByteArray, QString> _q_mapFromX509Name(const X509_NAME *name);
 
 bool QSslCertificate::operator==(const QSslCertificate &other) const
 {
@@ -125,9 +125,11 @@
     if (d->serialNumberString.isEmpty() && d->x509) {
         ASN1_INTEGER *serialNumber = q_X509_get_serialNumber(d->x509);
         QByteArray hexString;
-        hexString.reserve(serialNumber->length * 3);
-        for (int a = 0; a < serialNumber->length; ++a) {
-            hexString += QByteArray::number(serialNumber->data[a], 16).rightJustified(2, '0');
+        const unsigned char *serialNumberData = q_ASN1_STRING_get0_data(serialNumber);
+        const int serialNumberLength = q_ASN1_STRING_length(serialNumber);
+        hexString.reserve(serialNumberLength * 3);
+        for (int a = 0; a < serialNumberLength; ++a) {
+            hexString += QByteArray::number(serialNumberData[a], 16).rightJustified(2, '0');
             hexString += ':';
         }
         hexString.chop(1);
@@ -251,10 +253,10 @@
                 QHostAddress ipAddress;
                 switch (len) {
                 case 4: // IPv4
-                    ipAddress = QHostAddress(qFromBigEndian(*reinterpret_cast<quint32 *>(genName->d.iPAddress->data)));
+                    ipAddress = QHostAddress(qFromBigEndian<quint32>(q_ASN1_STRING_get0_data(genName->d.iPAddress)));
                     break;
                 case 16: // IPv6
-                    ipAddress = QHostAddress(reinterpret_cast<quint8 *>(genName->d.iPAddress->data));
+                    ipAddress = QHostAddress(q_ASN1_STRING_get0_data(genName->d.iPAddress));
                     break;
                 default: // Unknown IP address format
                     break;
@@ -329,7 +331,7 @@
 /*
  * Convert unknown extensions to a QVariant.
  */
-static QVariant x509UnknownExtensionToValue(X509_EXTENSION *ext)
+static QVariant x509UnknownExtensionToValue(QT_OPENSSL4_CONST X509_EXTENSION *ext)
 {
     Q_ASSERT(ext);
     // Get the extension specific method object if available,
@@ -338,7 +340,7 @@
     // in the object.
     X509V3_EXT_METHOD *meth = const_cast<X509V3_EXT_METHOD *>(q_X509V3_EXT_get(ext));
     if (!meth) {
-        ASN1_OCTET_STRING *value = q_X509_EXTENSION_get_data(ext);
+        QT_OPENSSL4_CONST ASN1_OCTET_STRING *value = q_X509_EXTENSION_get_data(ext);
         Q_ASSERT(value);
         QByteArray result( reinterpret_cast<const char *>(q_ASN1_STRING_get0_data(value)),
                            q_ASN1_STRING_length(value));
@@ -418,9 +420,9 @@
  * taken from RFC 5280, however we decided the capitalisation in the RFC
  * was too silly for the real world.
  */
-static QVariant x509ExtensionToValue(X509_EXTENSION *ext)
+static QVariant x509ExtensionToValue(QT_OPENSSL4_CONST X509_EXTENSION *ext)
 {
-    ASN1_OBJECT *obj = q_X509_EXTENSION_get_object(ext);
+    QT_OPENSSL4_CONST ASN1_OBJECT *obj = q_X509_EXTENSION_get_object(ext);
     int nid = q_OBJ_obj2nid(obj);
 
     // We cast away the const-ness here because some versions of openssl
@@ -511,8 +513,8 @@
 
             // keyid
             if (auth_key->keyid) {
-                QByteArray keyid(reinterpret_cast<const char *>(auth_key->keyid->data),
-                                 auth_key->keyid->length);
+                QByteArray keyid(reinterpret_cast<const char *>(q_ASN1_STRING_get0_data(auth_key->keyid)),
+                                 q_ASN1_STRING_length(auth_key->keyid));
                 result[QLatin1String("keyid")] = keyid.toHex();
             }
 
@@ -532,13 +534,13 @@
     return {};
 }
 
-QSslCertificateExtension QSslCertificatePrivate::convertExtension(X509_EXTENSION *ext)
+QSslCertificateExtension QSslCertificatePrivate::convertExtension(QT_OPENSSL4_CONST X509_EXTENSION *ext)
 {
     Q_ASSERT(ext);
 
     QSslCertificateExtension result;
 
-    ASN1_OBJECT *obj = q_X509_EXTENSION_get_object(ext);
+    QT_OPENSSL4_CONST ASN1_OBJECT *obj = q_X509_EXTENSION_get_object(ext);
     if (!obj) {
         qCWarning(lcSsl, "Invalid (nullptr) ASN1_OBJECT");
         return result;
@@ -586,7 +588,7 @@
     result.reserve(count);
 
     for (int i = 0; i < count; i++) {
-        X509_EXTENSION *ext = q_X509_get_ext(d->x509, i);
+        QT_OPENSSL4_CONST X509_EXTENSION *ext = q_X509_get_ext(d->x509, i);
         if (!ext) {
             qCWarning(lcSsl) << "Invalid (nullptr) extension at index" << i;
             continue;
@@ -699,7 +701,7 @@
     return QString::fromLatin1(result);
 }
 
-QByteArray QSslCertificatePrivate::asn1ObjectId(ASN1_OBJECT *object)
+QByteArray QSslCertificatePrivate::asn1ObjectId(const ASN1_OBJECT *object)
 {
     char buf[80]; // The openssl docs a buffer length of 80 should be more than enough
     q_OBJ_obj2txt(buf, sizeof(buf), object, 1); // the 1 says always use the oid not the long name
@@ -708,7 +710,7 @@
 }
 
 
-QByteArray QSslCertificatePrivate::asn1ObjectName(ASN1_OBJECT *object)
+QByteArray QSslCertificatePrivate::asn1ObjectName(const ASN1_OBJECT *object)
 {
     int nid = q_OBJ_obj2nid(object);
     if (nid != NID_undef)
@@ -717,11 +719,11 @@
     return asn1ObjectId(object);
 }
 
-static QMultiMap<QByteArray, QString> _q_mapFromX509Name(X509_NAME *name)
+static QMultiMap<QByteArray, QString> _q_mapFromX509Name(const X509_NAME *name)
 {
     QMultiMap<QByteArray, QString> info;
     for (int i = 0; i < q_X509_NAME_entry_count(name); ++i) {
-        X509_NAME_ENTRY *e = q_X509_NAME_get_entry(name, i);
+        QT_OPENSSL4_CONST X509_NAME_ENTRY *e = q_X509_NAME_get_entry(name, i);
 
         QByteArray name = QSslCertificatePrivate::asn1ObjectName(q_X509_NAME_ENTRY_get_object(e));
         unsigned char *data = nullptr;
