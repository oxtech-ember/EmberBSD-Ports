--- startkde/startplasma.cpp.orig
+++ startkde/startplasma.cpp
@@ -15,6 +15,7 @@
 
 #include <QDir>
 #include <QEventLoop>
+#include <QList>
 #include <QProcess>
 #include <QStandardPaths>
 #include <QTextStream>
@@ -407,6 +408,22 @@
     return std::make_pair(settings.lookAndFeelPackage(), KLookAndFeelManager::AllSettings);
 }
 
+static QByteArray appendInstalledDir(QByteArray dirs, const QByteArray &installed, const QByteArray &fallback)
+{
+    const bool usingDefault = dirs.isEmpty();
+    if (usingDefault) {
+        dirs = fallback;
+    }
+    if (!dirs.split(':').contains(installed)) {
+        if (usingDefault) {
+            dirs = installed + ':' + dirs;
+        } else {
+            dirs += ':' + installed;
+        }
+    }
+    return dirs;
+}
+
 void setupPlasmaEnvironment()
 {
     qputenv("KDE_FULL_SESSION", "true");
@@ -419,10 +436,8 @@
     qputenv("XDG_MENU_PREFIX", "plasma-");
 
     // Add kdedefaults dir to allow config defaults overriding from a writable location
-    QByteArray currentConfigDirs = qgetenv("XDG_CONFIG_DIRS");
-    if (currentConfigDirs.isEmpty()) {
-        currentConfigDirs = "/etc/xdg";
-    }
+    QByteArray currentConfigDirs = appendInstalledDir(qgetenv("XDG_CONFIG_DIRS"), KDE_INSTALL_FULL_CONFDIR, "/etc/xdg");
+    qputenv("XDG_DATA_DIRS", appendInstalledDir(qgetenv("XDG_DATA_DIRS"), KDE_INSTALL_FULL_DATAROOTDIR, "/usr/local/share:/usr/share"));
     const QString extraConfigDir = QStandardPaths::writableLocation(QStandardPaths::GenericConfigLocation) + QLatin1String("/kdedefaults");
     QDir().mkpath(extraConfigDir);
     qputenv("XDG_CONFIG_DIRS", QByteArray(QFile::encodeName(extraConfigDir) + ':' + currentConfigDirs));
