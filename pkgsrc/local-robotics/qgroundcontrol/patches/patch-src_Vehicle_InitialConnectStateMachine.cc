$NetBSD$

Origin: EmberBSD (AI-assisted), local, not submitted upstream.
Check for the latest stable firmware only when
FirmwareUpgrade/checkLatestStable is true.

--- src/Vehicle/InitialConnectStateMachine.cc.orig
+++ src/Vehicle/InitialConnectStateMachine.cc
@@ -14,6 +14,7 @@
 #include "QGCLoggingCategory.h"
 #include "SettingsManager.h"
 #include "MavlinkSettings.h"
+#include "FirmwareUpgradeSettings.h"
 
 #include <cstring>
 
@@ -337,7 +338,9 @@ void InitialConnectStateMachine::_handleAutopilotVersionSuccess(const mavlink_me
         vehicle()->_gitHash = nullStr;
     }
 
-    if (QGCCorePlugin::instance()->options()->checkFirmwareVersion() && !vehicle()->_checkLatestStableFWDone) {
+    if (QGCCorePlugin::instance()->options()->checkFirmwareVersion() &&
+        SettingsManager::instance()->firmwareUpgradeSettings()->checkLatestStable()->rawValue().toBool() &&
+        !vehicle()->_checkLatestStableFWDone) {
         vehicle()->_checkLatestStableFWDone = true;
         vehicle()->_firmwarePlugin->checkIfIsLatestStable(vehicle());
     }
