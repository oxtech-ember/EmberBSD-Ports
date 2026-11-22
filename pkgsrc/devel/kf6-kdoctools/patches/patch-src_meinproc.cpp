$NetBSD$

Origin: EmberBSD contributors (AI-assisted).
Run the selected XML validator with its original arguments and exit status.

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
@@ -125,8 +127,8 @@
             break;
         case CheckNoXmllint:
             DIE("Could not find xmllint");
-        case CheckNoOut:
-            DIE("`xmllint --noout` outputted text");
+        case CheckFailed:
+            DIE("xmllint validation failed");
         }
     }
 
