Origin: EmberBSD (AI-assisted), preserve SVG inputs and report conversion failures.
Use the selected input root instead of assuming its name is icons. A malformed
XML document must fail the generator even when it wrote partial output.

--- tools/generate-symbolic-dark.cpp.orig
+++ tools/generate-symbolic-dark.cpp
@@ -122,7 +122,7 @@
 
             // create dir, might be needed for symlink
             QDir outputDir = outputDirInfo.absoluteFilePath();
-            const auto outputFilePath = outputDir.absoluteFilePath(QString{inputFilePath}.remove(QRE(u".*/icons/"_s)));
+            const auto outputFilePath = outputDir.absoluteFilePath(inputDir.relativeFilePath(inputFilePath));
             QFileInfo outputFileInfo(outputFilePath);
             outputDir = outputFileInfo.dir();
             if (!outputDir.exists()) {
@@ -204,5 +204,5 @@
         qWarning().noquote() << elideString(xmlWriteErrorFiles.join("\n"_L1));
     }
 
-    return wasAnyFileWritten ? 0 : 1;
+    return wasAnyFileWritten && unreadFiles.isEmpty() && unwrittenFiles.isEmpty() && xmlReadErrorFiles.isEmpty() && xmlWriteErrorFiles.isEmpty() ? 0 : 1;
 }
