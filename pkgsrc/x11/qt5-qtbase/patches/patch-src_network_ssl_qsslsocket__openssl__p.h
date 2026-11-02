$NetBSD$

Build with OpenSSL 4, which adds const to the X.509 API and makes
ASN1_STRING opaque. Based on Qt 6 commit e806630e694d (QTBUG-145221).

--- src/network/ssl/qsslsocket_openssl_p.h.orig
+++ src/network/ssl/qsslsocket_openssl_p.h
@@ -102,6 +102,15 @@
 #include <openssl/tls1.h>
 #include <openssl/opensslv.h>
 
+// OpenSSL 4 adds const to the X.509 API and makes ASN1_STRING opaque.
+#ifndef QT_OPENSSL4_CONST
+#if defined(OPENSSL_VERSION_MAJOR) && OPENSSL_VERSION_MAJOR >= 4
+#define QT_OPENSSL4_CONST const
+#else
+#define QT_OPENSSL4_CONST
+#endif
+#endif
+
 #if QT_CONFIG(opensslv11)
 #include <openssl/dh.h>
 #endif
