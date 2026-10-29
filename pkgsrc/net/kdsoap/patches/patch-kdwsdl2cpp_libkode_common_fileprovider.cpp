$NetBSD$

Origin: EmberBSD (AI-assisted), not submitted upstream.
KDSoap_CODEGENERATOR_ONLY builds kdwsdl2cpp alone against QtCore and QtXml,
for a build host whose Qt has no QtNetwork. Remote WSDL downloads are then
refused; local files and -import-path work as before. The default build is
unchanged.

--- kdwsdl2cpp/libkode/common/fileprovider.cpp.orig
+++ kdwsdl2cpp/libkode/common/fileprovider.cpp
@@ -27,9 +27,11 @@
 #include <QUrl>
 #include <QDebug>
 #include <QDir>
+#ifndef KDWSDL2CPP_NO_NETWORK
 #include <QNetworkAccessManager>
 #include <QNetworkRequest>
 #include <QNetworkReply>
+#endif
 #include <QTemporaryFile>
 
 #ifndef Q_OS_WIN
@@ -113,6 +115,11 @@
     if (it != fileProviderCache.constEnd()) {
         data = it.value();
     } else {
+#ifdef KDWSDL2CPP_NO_NETWORK
+        qWarning("Cannot download '%s': kdwsdl2cpp was built without QtNetwork; use -import-path",
+                 url.toEncoded().constData());
+        return false;
+#else
         qDebug("Downloading '%s'", url.toEncoded().constData());
 
         QNetworkAccessManager manager;
@@ -133,6 +140,7 @@
         qDebug("Download successful");
         data = job->readAll();
         fileProviderCache[url] = data;
+#endif
     }
 
     QFile file(mFileName);
