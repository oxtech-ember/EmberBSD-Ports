$NetBSD$

Origin: EmberBSD contributors (AI-assisted).
Resolve data and tools within the selected installation during relocation.

--- src/xslt.cpp.orig
+++ src/xslt.cpp
@@ -21,11 +21,15 @@
 #include <libxslt/xsltutils.h>
 
 #include <QByteArray>
+#include <QCoreApplication>
 #include <QDir>
 #include <QFile>
 #include <QList>
 #include <QStandardPaths>
 #include <QString>
+#if RELOCATABLE_DOCBOOK_FILES && defined(Q_OS_UNIX) && defined(KDOCTOOLS_SHARED_LIBRARY)
+#include <dlfcn.h>
+#endif
 #include <QUrl>
 
 #if !defined(SIMPLE_XSLT)
@@ -379,6 +383,22 @@
     const QString fileName = QStringLiteral("kf6/kdoctools/") + file;
     QStringList result = QStandardPaths::locateAll(QStandardPaths::GenericDataLocation, fileName, option);
 
+#if RELOCATABLE_DOCBOOK_FILES && defined(Q_OS_UNIX)
+#ifdef KDOCTOOLS_SHARED_LIBRARY
+    Dl_info image{};
+    if (dladdr(&s_dtdDirs, &image) && image.dli_fname) {
+        const QString imagePath = QFileInfo(QFile::decodeName(image.dli_fname)).canonicalFilePath();
+        if (!imagePath.isEmpty()) {
+            const QString relative = QStringLiteral(KDOCTOOLS_LIBDIR_TO_DATADIR_KF "/kdoctools/") + file;
+            const QFileInfo resource(QFileInfo(imagePath).dir(), relative);
+            const bool found = option == QStandardPaths::LocateFile ? resource.isFile() : resource.isDir();
+            if (found && !result.contains(resource.absoluteFilePath())) {
+                result.append(resource.absoluteFilePath());
+            }
+        }
+    }
+#endif
+#else
     // fallback to stuff installed with KDocTools
     const QFileInfo fileInInstallDataDir(QStringLiteral(KDOCTOOLS_INSTALL_DATADIR_KF) + QStringLiteral("/kdoctools/") + file);
     if (fileInInstallDataDir.exists()) {
@@ -387,6 +407,17 @@
         }
         if ((option == QStandardPaths::LocateDirectory) && fileInInstallDataDir.isDir()) {
             result.append(fileInInstallDataDir.absoluteFilePath());
+        }
+    }
+#endif
+
+    // fallback to the data next to the running tool, for a relocated prefix
+    if (QCoreApplication::instance()) {
+        const QFileInfo fileInAppDataDir(QCoreApplication::applicationDirPath() + QLatin1Char('/') + QStringLiteral(KDOCTOOLS_BINDIR_TO_DATADIR_KF)
+                                         + QStringLiteral("/kdoctools/") + file);
+        const bool found = (option == QStandardPaths::LocateFile) ? fileInAppDataDir.isFile() : fileInAppDataDir.isDir();
+        if (found && !result.contains(fileInAppDataDir.absoluteFilePath())) {
+            result.append(fileInAppDataDir.absoluteFilePath());
         }
     }
 
