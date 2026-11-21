$NetBSD$

Origin: EmberBSD (AI-assisted), not submitted upstream.
KDSoap_CODEGENERATOR_ONLY builds kdwsdl2cpp alone against QtCore and QtXml,
for a build host whose Qt has no QtNetwork. Remote WSDL downloads are then
refused; local files and -import-path work as before. The default build is
unchanged.

--- kdwsdl2cpp/src/main.cpp.orig
+++ kdwsdl2cpp/src/main.cpp
@@ -13,9 +13,11 @@
 #include <QDir>
 #include <QFile>
 #include <QFileInfo>
+#ifndef KDWSDL2CPP_NO_NETWORK
 #include <QNetworkAccessManager>
 #include <QSslCertificate>
 #include <QSslKey>
+#endif
 #include <QTimer>
 
 static const char *WSDL2CPP_DESCRIPTION = "KDAB's WSDL to C++ compiler";
@@ -64,7 +66,7 @@
         QCommandLineOption useLocalFilesOnly {"use-local-files-only", "Only use local files instead of downloading them automatically.\n"
                                                                       "This can be used to force the correct use of the import-path option."};
         QCommandLineOption helpOnMissing {"help-on-missing", "When groups or basic types could not be found, display available types (helps with wrong namespaces)."};
-#if !defined(QT_NO_SSL)
+#if !defined(QT_NO_SSL) && !defined(KDWSDL2CPP_NO_NETWORK)
         QCommandLineOption pkcs12File {"pkcs12file", "Load a certificate from a PKCS12 file.\n"
                                                      "You can use this option if the WSDL file (or files referring to it) is served from a location which requires certificate based authentication.",
                                        "pkcs12file"};
@@ -90,7 +92,7 @@
                        options.importPath,
                        options.useLocalFilesOnly,
                        options.helpOnMissing,
-#if !defined(QT_NO_SSL)
+#if !defined(QT_NO_SSL) && !defined(KDWSDL2CPP_NO_NETWORK)
                        options.pkcs12File,
                        options.pkcs12Password,
 #endif
@@ -195,7 +197,7 @@
     Settings::self()->setSkipAsyncJobs(parser.isSet(options.noAsyncJobs));
 
     KWSDL::Compiler compiler;
-#if !defined(QT_NO_SSL)
+#if !defined(QT_NO_SSL) && !defined(KDWSDL2CPP_NO_NETWORK)
     const QString pkcs12File = parser.value(options.pkcs12File),
                   pkcs12Password = parser.value(options.pkcs12Password);
     if (!pkcs12File.isEmpty()) {
