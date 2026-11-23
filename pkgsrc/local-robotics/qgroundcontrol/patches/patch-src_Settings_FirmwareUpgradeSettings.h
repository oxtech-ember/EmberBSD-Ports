$NetBSD$

Origin: EmberBSD (AI-assisted), local, not submitted upstream.
Declare the FirmwareUpgrade/checkLatestStable setting.

--- src/Settings/FirmwareUpgradeSettings.h.orig
+++ src/Settings/FirmwareUpgradeSettings.h
@@ -17,4 +17,5 @@ class FirmwareUpgradeSettings : public SettingsGroup
     DEFINE_SETTINGFACT(defaultFirmwareType)
     DEFINE_SETTINGFACT(apmChibiOS)
     DEFINE_SETTINGFACT(apmVehicleType)
+    DEFINE_SETTINGFACT(checkLatestStable)
 };
