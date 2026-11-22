$NetBSD$

Origin: EmberBSD contributors (AI-assisted).
Run the selected XML validator with its original arguments and exit status.

--- src/meinproc_common.cpp.orig
+++ src/meinproc_common.cpp
@@ -4,22 +4,11 @@
 #include "docbookxslt.h"
 #include "docbookxslt_p.h"
 
-#include <QDir>
 #include <QFileInfo>
+#include <QProcess>
+#include <QProcessEnvironment>
 
-#include <cstdlib>
-
-#ifdef Q_CC_MSVC
-static inline FILE *popen(const char *command, const char *mode)
-{
-    return _popen(command, mode);
-}
-
-static inline int pclose(FILE *file)
-{
-    return _pclose(file);
-}
-#endif
+#include <cstdio>
 
 CheckFileResult checkFile(const QString &checkFilename)
 {
@@ -38,32 +27,28 @@
 
 CheckResult check(const QString &checkFilename, const QString &exe, const QByteArray &catalogs)
 {
-    const QString pwd_buffer = QDir::currentPath();
+    if (!QFileInfo(exe).isExecutable()) {
+        return CheckNoXmllint;
+    }
+
     const QFileInfo file(checkFilename);
-
-    qputenv("XML_CATALOG_FILES", catalogs);
-    if (QFileInfo(exe).isExecutable()) {
-        QDir::setCurrent(file.absolutePath());
-        QString cmd = exe;
-        cmd += QStringLiteral(" --valid --noout ");
-        cmd += file.fileName();
-        cmd += QStringLiteral(" 2>&1");
-        FILE *xmllint = popen(QFile::encodeName(cmd).constData(), "r");
-        char buf[512];
-        bool noout = true;
-        size_t n;
-        while ((n = fread(buf, 1, sizeof(buf) - 1, xmllint))) {
-            noout = false;
-            buf[n] = '\0';
-            fputs(buf, stderr);
-        }
-        pclose(xmllint);
-        QDir::setCurrent(pwd_buffer);
-        if (!noout) {
-            return CheckNoOut;
-        }
-    } else {
+    auto environment = QProcessEnvironment::systemEnvironment();
+    environment.insert(QStringLiteral("XML_CATALOG_FILES"), QString::fromLocal8Bit(catalogs));
+    QProcess validator;
+    validator.setProcessEnvironment(environment);
+    validator.setWorkingDirectory(file.absolutePath());
+    validator.setProcessChannelMode(QProcess::MergedChannels);
+    validator.start(exe, {QStringLiteral("--valid"), QStringLiteral("--noout"), file.absoluteFilePath()});
+    if (!validator.waitForStarted(-1)) {
         return CheckNoXmllint;
+    }
+    const bool finished = validator.waitForFinished(-1);
+    const QByteArray output = validator.readAll();
+    if (!output.isEmpty()) {
+        std::fwrite(output.constData(), 1, static_cast<size_t>(output.size()), stderr);
+    }
+    if (!finished || validator.exitStatus() != QProcess::NormalExit || validator.exitCode() != 0 || !output.isEmpty()) {
+        return CheckFailed;
     }
     return CheckSuccess;
 }
