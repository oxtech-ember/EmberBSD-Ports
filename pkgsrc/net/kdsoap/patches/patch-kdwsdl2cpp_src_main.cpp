$NetBSD$

Origin: EmberBSD (AI-assisted), not submitted upstream.
KDSoap_CODEGENERATOR_ONLY builds kdwsdl2cpp alone against QtCore and QtXml,
for a build host whose Qt has no QtNetwork. Remote WSDL downloads are then
refused; local files and -import-path work as before. The default build is
unchanged.

--- kdwsdl2cpp/src/main.cpp.orig
+++ kdwsdl2cpp/src/main.cpp
@@ -12,9 +12,11 @@
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
@@ -57,7 +59,7 @@
             "                            use of the import-path option\n"
             "  -help-on-missing          When groups or basic types could not be found, display\n"
             "                            available types (helps with wrong namespaces)\n"
-#if !defined(QT_NO_SSL)
+#if !defined(QT_NO_SSL) && !defined(KDWSDL2CPP_NO_NETWORK)
             "  -pkcs12file               Load a certificate from a PKCS12 file. You can use this option\n"
             "                            if the WSDL file (or files referring to it) is served from a \n"
             "                            location which require certificate based authentication\n"
@@ -96,7 +98,7 @@
     bool useLocalFilesOnly = false;
     bool helpOnMissing = false;
     bool skipAsync = false, skipSync = false, skipAsyncJobs = false;
-#if !defined(QT_NO_SSL)
+#if !defined(QT_NO_SSL) && !defined(KDWSDL2CPP_NO_NETWORK)
     QString pkcs12File, pkcs12Password;
 #endif
 
@@ -216,7 +218,7 @@
             useLocalFilesOnly = true;
         } else if (opt == QLatin1String("-help-on-missing")) {
             helpOnMissing = true;
-#if !defined(QT_NO_SSL)
+#if !defined(QT_NO_SSL) && !defined(KDWSDL2CPP_NO_NETWORK)
         } else if (opt == QLatin1String("-pkcs12file")) {
             ++arg;
             if (!argv[arg]) {
@@ -296,7 +298,7 @@
     Settings::self()->setSkipAsyncJobs(skipAsyncJobs);
 
     KWSDL::Compiler compiler;
-#if !defined(QT_NO_SSL)
+#if !defined(QT_NO_SSL) && !defined(KDWSDL2CPP_NO_NETWORK)
     if (!pkcs12File.isEmpty()) {
         QFile certFile(pkcs12File);
         if (certFile.open(QFile::ReadOnly)) {
