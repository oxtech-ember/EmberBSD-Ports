$NetBSD$

Identify the local OS update service during notifier startup.

--- notifier/DiscoverNotifier.h.orig
+++ notifier/DiscoverNotifier.h
@@ -54,6 +54,7 @@
         return m_hasSecurityUpdates;
     }
     bool isSystemUpdateable() const;
+    bool usesSystemUpdateService() const { return m_systemNotifier != nullptr && m_backends.size() == 1; }
 
     QStringList loadedModules() const;
     bool needsReboot() const
@@ -104,6 +105,7 @@
     QTimer m_timer;
     bool m_hasSecurityUpdates = false;
     bool m_hasUpdates = false;
+    BackendNotifierModule *m_systemNotifier = nullptr;
     bool m_needsReboot = false;
     bool m_isBusy = false;
     QPointer<KNotification> m_updatesAvailableNotification;
