$NetBSD$

Name the system from uname when os-release is not present.

--- kcms/about-distro/src/main.cpp.orig	2026-10-27 14:26:08.000000000 +0300
+++ kcms/about-distro/src/main.cpp	2026-11-07 23:24:31.038060097 +0300
@@ -8,7 +8,9 @@
 
 #include <QAbstractListModel>
 #include <QClipboard>
+#include <QFile>
 #include <QFileInfo>
+#include <sys/utsname.h>
 #include <QGuiApplication>
 #include <QIcon>
 #include <QLocale>
@@ -176,9 +178,22 @@
         }
 
         // as a product brand is different from Kubuntu.
-        const QString distroName = cg.readEntry("Name", os.name());
+        QString distroName = cg.readEntry("Name", os.name());
         const QString osrVersion = cg.readEntry("UseOSReleaseVersion", false) ? os.version() : os.versionId();
-        const QString versionId = cg.readEntry("Version", osrVersion);
+        QString versionId = cg.readEntry("Version", osrVersion);
+#if defined(Q_OS_NETBSD)
+        // NetBSD has /etc/release. KOSRelease falls back to a Linux name
+        // when /etc/os-release is absent.
+        if (!QFile::exists(QStringLiteral("/etc/os-release"))) {
+            struct utsname name {};
+            if (uname(&name) == 0) {
+                distroName = QString::fromLocal8Bit(name.sysname);
+                if (versionId.isEmpty()) {
+                    versionId = QString::fromLocal8Bit(name.release);
+                }
+            }
+        }
+#endif
 
         auto versionEntry = new OSVersionEntry(distroName, versionId, showBuild ? os.buildId() : QString());
         // This creates a trailing space if versionId is empty, so trimming String
