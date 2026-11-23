$NetBSD$

Origin: EmberBSD (AI-assisted), local, not submitted upstream.
Define the FirmwareUpgrade/checkLatestStable setting.

--- src/Settings/FirmwareUpgradeSettings.cc.orig
+++ src/Settings/FirmwareUpgradeSettings.cc
@@ -7,3 +7,4 @@ DECLARE_SETTINGGROUP(FirmwareUpgrade, "FirmwareUpgrade")
 DECLARE_SETTINGSFACT(FirmwareUpgradeSettings, defaultFirmwareType)
 DECLARE_SETTINGSFACT(FirmwareUpgradeSettings, apmChibiOS)
 DECLARE_SETTINGSFACT(FirmwareUpgradeSettings, apmVehicleType)
+DECLARE_SETTINGSFACT(FirmwareUpgradeSettings, checkLatestStable)
