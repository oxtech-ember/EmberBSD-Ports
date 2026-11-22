$NetBSD$

Origin: EmberBSD contributors (AI-assisted).
Locate the SDK iso-codes data relative to its Darwin shared library.

--- src/localedata/isocodescache.cpp.orig
+++ src/localedata/isocodescache.cpp
@@ -18,6 +18,10 @@
 #include <QJsonObject>
 #include <QStandardPaths>
 
+#ifdef KI18N_ISO_CODES_RELATIVE_DIR
+#include <dlfcn.h>
+#endif
+
 using namespace Qt::Literals;
 
 // increment those when changing the format
@@ -34,6 +38,18 @@
         return path;
     }
 
+#ifdef KI18N_ISO_CODES_RELATIVE_DIR
+    Dl_info image{};
+    if (dladdr(reinterpret_cast<const void *>(&isoCodesPath), &image) && image.dli_fname) {
+        const QString libraryDir = QFileInfo(QString::fromLocal8Bit(image.dli_fname)).canonicalPath();
+        if (!libraryDir.isEmpty()) {
+            path = QDir(libraryDir).filePath(QLatin1String(KI18N_ISO_CODES_RELATIVE_DIR) + QLatin1Char('/') + file);
+            if (QFileInfo(path).isFile()) {
+                return path;
+            }
+        }
+    }
+#else
     // search manually in the compile-time determined prefix
     // needed for example for non-installed Windows binaries to work, such as unit tests
     for (const char *installLocation : {"/share", "/bin/data"}) {
@@ -43,6 +59,7 @@
         }
     }
 
+#endif
     return {};
 #else
     return QLatin1String("assets:/share/iso-codes/json/") + file;
