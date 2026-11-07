$NetBSD$

kirigami-addons 1.10 installs KirigamiApp, not KirigamiAppDefaults.
The header is include/KirigamiAddons/App/KirigamiApp. The constructor
performs the setup that KirigamiAppDefaults::apply() performed.

--- discover/main.cpp.orig
+++ discover/main.cpp
@@ -24,7 +24,7 @@
 #include <qtwebviewfunctions.h>
 #endif
 
-#include <KirigamiAppDefaults>
+#include <KirigamiApp>
 #include <QProcessEnvironment>
 
 std::unique_ptr<QCommandLineParser> createParser()
@@ -111,7 +111,11 @@
 #endif
 
     QApplication app(argc, argv);
-    KirigamiAppDefaults::apply(&app);
+    // kirigami-addons 1.10 replaced KirigamiAppDefaults::apply() with
+    // KirigamiApp. Construct it after QApplication. The constructor
+    // applies the same style, icon and colour setup. Keep the object
+    // alive for the process.
+    [[maybe_unused]] KirigamiApp kirigamiApp;
 
     app.setWindowIcon(QIcon::fromTheme(QStringLiteral("plasmadiscover")));
     app.setQuitLockEnabled(false);
