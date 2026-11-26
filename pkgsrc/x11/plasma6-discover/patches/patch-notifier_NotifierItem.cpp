$NetBSD$

Use the Updates page for the system action.

--- notifier/NotifierItem.cpp.orig
+++ notifier/NotifierItem.cpp
@@ -43,9 +43,11 @@
         }
     });
 
-    auto updatesAction =
-        menu->addAction(QIcon::fromTheme(QStringLiteral("system-software-update")), i18nc("@action:button Starts an update in the background", "Start Update"));
-    connect(updatesAction, &QAction::triggered, &m_notifier, &DiscoverNotifier::startUnattendedUpdates);
+    if (!m_notifier.usesSystemUpdateService()) {
+        auto updatesAction =
+            menu->addAction(QIcon::fromTheme(QStringLiteral("system-software-update")), i18nc("@action:button Starts an update in the background", "Start Update"));
+        connect(updatesAction, &QAction::triggered, &m_notifier, &DiscoverNotifier::startUnattendedUpdates);
+    }
 
     auto refreshAction = menu->addAction(QIcon::fromTheme(QStringLiteral("view-refresh")), i18n("Refresh…"));
     connect(refreshAction, &QAction::triggered, &m_notifier, &DiscoverNotifier::recheckSystemUpdateNeededAndNotifyApp);
