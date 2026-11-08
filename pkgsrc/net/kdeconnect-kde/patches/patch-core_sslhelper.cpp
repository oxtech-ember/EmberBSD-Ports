$NetBSD$

LibreSSL returns a const X509_NAME from X509_get_subject_name.

--- core/sslhelper.cpp.orig
+++ core/sslhelper.cpp
@@ -169,7 +169,8 @@
     }
 
     // Set the certificate subject and issuer (self-signed).
-    auto name = X509_get_subject_name(x509.get());
+    // LibreSSL's X509_get_subject_name returns a const name. The calls below write it.
+    auto name = const_cast<X509_NAME *>(X509_get_subject_name(x509.get()));
     QByteArray commonNameBytes = commonName.toLatin1();
     const unsigned char *commonNameCStr = reinterpret_cast<const unsigned char *>(commonNameBytes.data());
     if (!X509_NAME_add_entry_by_txt(name, "CN", MBSTRING_ASC, commonNameCStr, -1, -1, 0)) { // Common Name
