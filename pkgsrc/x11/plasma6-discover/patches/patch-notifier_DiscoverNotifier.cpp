$NetBSD$

Read local reboot state on startup and changes. Leave unattended updates to the OS service.

--- notifier/DiscoverNotifier.cpp.orig
+++ notifier/DiscoverNotifier.cpp
@@ -60,7 +60,6 @@
         qWarning() << "QNetworkInformation has no backend. Is NetworkManager.service running?";
     }
 
-    refreshUnattended();
     connect(m_settingsWatcher.data(), &KConfigWatcher::configChanged, this, [this](const KConfigGroup &group, const QByteArrayList &names) {
         if (group.config()->name() != m_settings->config()->name() || group.name() != QLatin1String("Global")) {
             return;
@@ -74,22 +73,16 @@
     m_backends = BackendNotifierFactory().allBackends();
     for (BackendNotifierModule *module : std::as_const(m_backends)) {
         connect(module, &BackendNotifierModule::foundUpdates, this, &DiscoverNotifier::updateStatusNotifier);
-        connect(module, &BackendNotifierModule::needsRebootChanged, this, [this]() {
-            // If we are using offline updates, there is no need to badger the user to
-            // reboot since it is safe to continue using the system in its current state
-            if (!m_needsReboot && !m_settings->useUnattendedUpdates()) {
-                m_needsReboot = true;
-                showRebootNotification();
-                Q_EMIT stateChanged();
-                Q_EMIT needsRebootChanged(true);
-            }
-        });
+        if (module->metaObject()->indexOfProperty("emberUpdateStatus") >= 0)
+            m_systemNotifier = module;
+        connect(module, &BackendNotifierModule::needsRebootChanged, this, &DiscoverNotifier::updateStatusNotifier);
 
         connect(module, &BackendNotifierModule::foundUpgradeAction, this, &DiscoverNotifier::foundUpgradeAction);
     }
     connect(&m_timer, &QTimer::timeout, this, &DiscoverNotifier::showUpdatesNotification);
     m_timer.setSingleShot(true);
     m_timer.setInterval(1s);
+    refreshUnattended();
     updateStatusNotifier();
 
     // Only fetch updates after the system is comfortably booted
@@ -189,7 +182,7 @@
 
 bool DiscoverNotifier::proceedUnattended() const
 {
-    if (!checkTriggerTimes(m_settings->lastUnattendedTrigger())) {
+    if (usesSystemUpdateService() || !checkTriggerTimes(m_settings->lastUnattendedTrigger())) {
         return false;
     }
 
@@ -239,8 +232,19 @@
 
     qCDebug(NOTIFIER) << "updateStatusNotifier: hasUpdates" << hasUpdates << "hasSecurityUpdates" << hasSecurityUpdates;
 
-    if (m_hasUpdates == hasUpdates && m_hasSecurityUpdates == hasSecurityUpdates)
-        return;
+    const bool needsReboot = kContains(m_backends, [](BackendNotifierModule *module) { return module->needsReboot(); });
+    if (m_needsReboot != needsReboot) {
+        m_needsReboot = needsReboot;
+        if (needsReboot && (usesSystemUpdateService() || !m_settings->useUnattendedUpdates()))
+            showRebootNotification();
+        Q_EMIT needsRebootChanged(needsReboot);
+        Q_EMIT stateChanged();
+    }
+    if (m_hasUpdates == hasUpdates && m_hasSecurityUpdates == hasSecurityUpdates) {
+        if (usesSystemUpdateService())
+            Q_EMIT stateChanged();
+        return;
+    }
 
     m_hasSecurityUpdates = hasSecurityUpdates;
     m_hasUpdates = hasUpdates;
@@ -327,7 +331,7 @@
         return RebootRequired;
     else if (m_isBusy)
         return Busy;
-    else if (!isOnline())
+    else if (!usesSystemUpdateService() && !isOnline())
         return Offline;
     else if (m_hasSecurityUpdates)
         return SecurityUpdates;
@@ -358,6 +362,8 @@
 
 QString DiscoverNotifier::message() const
 {
+    if (usesSystemUpdateService())
+        return m_systemNotifier->property("emberUpdateStatus").toString().toHtmlEscaped();
     switch (state()) {
     case SecurityUpdates:
         return i18n("Security updates available");
