$NetBSD$

Preserve NetBSD daemon startup, resolver diagnostics, TEST-NET-2 route probe, and privilege-drop behavior from commits 262ae2dd663, bd2c22674a2, and d55e659.

--- mDNSPosix/PosixDaemon.c
+++ mDNSPosix/PosixDaemon.c
@@ -51,6 +51,10 @@
 #include "PlatformCommon.h"
 #include "SCCSVersioning.h"
 
+#ifndef MDNSD_USER
+#define MDNSD_USER "nobody"
+#endif
+
 #ifndef UNICAST_DISABLED
 #define CONFIG_FILE "/etc/mdnsd.conf"
 static domainname DynDNSZone;                // Default wide-area zone for service registration
@@ -92,10 +96,10 @@
 {
 #ifndef UNICAST_DISABLED
     mDNSAddr DynDNSIP;
-    const mDNSAddr dummy = { mDNSAddrType_IPv4, { { { 1, 1, 1, 1 } } } };;
+    const mDNSAddr dummy = { mDNSAddrType_IPv4, { { { 198, 51, 100, 42 } } } };;
     mDNS_SetPrimaryInterfaceInfo(m, NULL, NULL, NULL);
     if (ParseDNSServers(m, uDNS_SERVERS_FILE) < 0)
-        LogMsg("Unable to parse DNS server list. Unicast DNS-SD unavailable");
+        LogInfo("Unable to parse DNS server list. Unicast DNS-SD unavailable");
     ReadDDNSSettingsFromConfFile(m, CONFIG_FILE, &DynDNSHostname, &DynDNSZone, NULL);
     mDNSPlatformSourceAddrForDest(&DynDNSIP, &dummy);
     if (DynDNSHostname.c[0]) mDNS_AddDynDNSHostName(m, &DynDNSHostname, NULL, NULL);
@@ -141,6 +145,33 @@
 
     getLocalTimestampNow(timestamp, sizeof(timestamp));
     LogRedact(MDNS_LOG_CATEGORY_DEFAULT, MDNS_LOG_DEFAULT, "---- END STATE LOG ---- (%s mDNSResponder Build %d.%02d.%02d)", timestamp, major_version, minor_version1, minor_version2);
+}
+
+mDNSlocal mStatus DropPrivileges(void)
+{
+    const struct passwd *pw = getpwnam(MDNSD_USER);
+    if (pw != NULL)
+    {
+        if (setgid(pw->pw_gid) < 0)
+        {
+            LogRedact(MDNS_LOG_CATEGORY_DEFAULT, MDNS_LOG_ERROR,
+                      "WARNING: mdnsd continuing as group root because setgid to \"" MDNSD_USER "\" failed with " PUB_S, strerror(errno));
+        }
+        if (setuid(pw->pw_uid) < 0)
+        {
+            LogMsg("WARNING: mdnsd continuing as root because setuid to \"" MDNSD_USER "\" failed with %s", strerror(errno));
+        }
+    }
+    else
+    {
+#ifdef MDNSD_NOROOT
+        LogMsg("WARNING: mdnsd exiting because user \"" MDNSD_USER "\" does not exist");
+        return mStatus_Invalid;
+#else
+        LogMsg("WARNING: mdnsd continuing as root because user \"" MDNSD_USER "\" does not exist");
+#endif
+    }
+    return mStatus_NoError;
 }
 
 mDNSlocal mStatus MainLoop(mDNS *m) // Loop until we quit.
@@ -210,27 +241,8 @@
 
     Reconfigure(&mDNSStorage);
 
-    // Now that we're finished with anything privileged, switch over to running as "nobody"
-    if (mStatus_NoError == err)
-    {
-        const struct passwd *pw = getpwnam("nobody");
-        if (pw != NULL)
-        {
-            if (setgid(pw->pw_gid) < 0)
-            {
-                LogRedact(MDNS_LOG_CATEGORY_DEFAULT, MDNS_LOG_ERROR,
-                          "WARNING: mdnsd continuing as group root because setgid to \"nobody\" failed with " PUB_S, strerror(errno));
-            }
-            if (setuid(pw->pw_uid) < 0)
-            {
-                LogMsg("WARNING: mdnsd continuing as root because setuid to \"nobody\" failed with %s", strerror(errno));
-            }
-        }
-        else
-        {
-            LogMsg("WARNING: mdnsd continuing as root because user \"nobody\" does not exist");
-        }
-    }
+    // Now that we're finished with anything privileged, switch over to the configured service user.
+    if (mStatus_NoError == err) err = DropPrivileges();
 
     if (mStatus_NoError == err)
         err = MainLoop(&mDNSStorage);
