$NetBSD$

Use the Kirigami defaults available in addons 1.10.

--- src/print-queue/main.cpp.orig
+++ src/print-queue/main.cpp
@@ -13,7 +13,35 @@
 #include <KDBusService>
 #include <KLocalizedString>
 #include <KWindowSystem>
-#include <KirigamiAppDefaults>
+#include <KColorSchemeManager>
+#include <KConfigGroup>
+#include <KIconTheme>
+#include <KSharedConfig>
+#include <QIcon>
+#include <QQuickStyle>
+#include <QSurfaceFormat>
+
+namespace {
+void applyKirigamiDefaults(QApplication *application)
+{
+    auto format = QSurfaceFormat::defaultFormat();
+    format.setOption(QSurfaceFormat::ResetNotification);
+    QSurfaceFormat::setDefaultFormat(format);
+    KColorSchemeManager::instance();
+    const QString initialStyle = QQuickStyle::name();
+    QIcon::setFallbackThemeName(QStringLiteral("breeze"));
+    if (qEnvironmentVariableIsEmpty("QT_QUICK_CONTROLS_STYLE") && initialStyle == QQuickStyle::name()) {
+        QQuickStyle::setStyle(QStringLiteral("org.kde.desktop"));
+        if (!qEnvironmentVariableIsSet("QT_STYLE_OVERRIDE")) {
+            const QString styleToUse = KConfigGroup(KSharedConfig::openConfig(), QStringLiteral("KDE")).readEntry("widgetStyle", QString());
+            if (styleToUse.isEmpty() || !QApplication::setStyle(styleToUse)) {
+                QApplication::setStyle(QStringLiteral("breeze"));
+            }
+        }
+    }
+    KIconTheme::initTheme();
+}
+}
 
 #include "PrintQueue.h"
 #include "config.h"
@@ -30,7 +58,7 @@
 {
     QCoreApplication::setAttribute(Qt::AA_DisableSessionManager);
     QApplication app(argc, argv);
-    KirigamiAppDefaults::apply(&app);
+    applyKirigamiDefaults(&app);
 
     app.setWindowIcon(QIcon::fromTheme(u"printer"_s));
     KLocalizedString::setApplicationDomain("org.kde.plasma.printqueue");
