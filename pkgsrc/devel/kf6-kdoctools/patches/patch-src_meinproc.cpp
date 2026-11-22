$NetBSD$

Origin: EmberBSD contributors (AI-assisted).
Resolve data and tools within the selected installation during relocation.

--- src/meinproc.cpp.orig
+++ src/meinproc.cpp
@@ -112,7 +112,9 @@
         }
         QByteArray catalogs = lst.join(" ").toLocal8Bit();
         QString exe;
-#if defined(XMLLINT)
+#if RELOCATABLE_DOCBOOK_FILES && defined(Q_OS_UNIX)
+        exe = QDir(QCoreApplication::applicationDirPath()).filePath(QStringLiteral("xmllint"));
+#elif defined(XMLLINT)
         exe = QStringLiteral(XMLLINT);
 #endif
         if (!QFileInfo(exe).isExecutable()) {
