$NetBSD$

Honor the Init advertise-local-address setting independently of service count.

--- mDNSCore/mDNS.c.orig
+++ mDNSCore/mDNS.c
@@ -1420,7 +1420,7 @@
             m->AutoTargetServices--;
             LogRedact(MDNS_LOG_CATEGORY_STATE, MDNS_LOG_DEBUG, "DecrementAutoTargetServices: AutoTargetServices %u Record " PRI_S,
                 m->AutoTargetServices, ARDisplayString(m, rr));
-            if (m->AutoTargetServices == 0)
+            if (m->AutoTargetServices == 0 && !m->AdvertiseLocalAddresses)
             {
                 for (intf = m->HostInterfaces; intf; intf = intf->next)
                 {
@@ -13936,7 +13936,7 @@
 
 mDNSlocal void AdvertiseInterfaceIfNeeded(mDNS *const m, NetworkInterfaceInfo *set)
 {
-    if (m->AutoTargetServices > 0) AdvertiseInterface(m, set);
+    if (m->AdvertiseLocalAddresses || m->AutoTargetServices > 0) AdvertiseInterface(m, set);
 }
 
 mDNSlocal void DeadvertiseInterface(mDNS *const m, NetworkInterfaceInfo *set, DeadvertiseFlags flags)
