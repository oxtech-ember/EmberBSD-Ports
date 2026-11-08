$NetBSD$

NetBSD stdio macros rename a local variable named stdout.

--- src/public/controller.cpp.orig
+++ src/public/controller.cpp
@@ -62,18 +62,18 @@
 
     connect(process, &QProcess::finished, [=](int exitCode, QProcess::ExitStatus exitStatus) {
         process->deleteLater();
-        const QString stdout = QString(process->readAllStandardOutput().trimmed());
+        const QString commandOutput = QString(process->readAllStandardOutput().trimmed());
 
         // Success
         if (exitCode == 0 && exitStatus == QProcess::NormalExit) {
-            callback.call({exitCode, stdout});
+            callback.call({exitCode, commandOutput});
             return;
         }
 
         // Failure
         QString intermediateText = QString(process->readAllStandardError().trimmed());
         if (intermediateText.isEmpty()) {
-            intermediateText = stdout;
+            intermediateText = commandOutput;
             if (intermediateText.isEmpty()) {
                 intermediateText = i18nc("@info:progress", "No error message provided");
             }
