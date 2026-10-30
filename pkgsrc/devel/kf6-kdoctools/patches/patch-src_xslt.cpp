$NetBSD$

Origin: EmberBSD (AI-assisted), not submitted upstream.
Find the KDocTools data relative to the running executable as well,
so tools from a relocated or selected prefix find their own data.

--- src/xslt.cpp.orig
+++ src/xslt.cpp
@@ -21,6 +21,7 @@
 #include <libxslt/xsltutils.h>
 
 #include <QByteArray>
+#include <QCoreApplication>
 #include <QDir>
 #include <QFile>
 #include <QList>
@@ -390,6 +391,16 @@
         }
     }
 
+    // fallback to the data next to the running tool, for a relocated prefix
+    if (QCoreApplication::instance()) {
+        const QFileInfo fileInAppDataDir(QCoreApplication::applicationDirPath() + QLatin1Char('/') + QStringLiteral(KDOCTOOLS_BINDIR_TO_DATADIR_KF)
+                                         + QStringLiteral("/kdoctools/") + file);
+        const bool found = (option == QStandardPaths::LocateFile) ? fileInAppDataDir.isFile() : fileInAppDataDir.isDir();
+        if (found && !result.contains(fileInAppDataDir.absoluteFilePath())) {
+            result.append(fileInAppDataDir.absoluteFilePath());
+        }
+    }
+
     if (result.isEmpty()) {
         qCDebug(KDocToolsLog) << "Could not locate file" << fileName << "in" << QStandardPaths::standardLocations(QStandardPaths::GenericDataLocation);
     }
