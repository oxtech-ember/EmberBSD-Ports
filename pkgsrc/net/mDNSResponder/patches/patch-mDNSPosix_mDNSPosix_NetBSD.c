$NetBSD$

Preserve NetBSD startup and transient multicast-send behavior from the prior OS import:
IPv6 socket failure handling is PR bin/57769 (commit b5ac9b23887);
EADDRNOTAVAIL is transient (commit 7f35ea7608f).

--- mDNSPosix/mDNSPosix.c
+++ mDNSPosix/mDNSPosix.c
@@ -159,6 +159,17 @@
 #pragma mark ***** Send and Receive
 #endif
 
+mDNSlocal mDNSBool mDNSPosixShouldReturnTransientSendError(int error, mDNSBool multicast)
+{
+    if (!multicast && (error == EHOSTDOWN || error == ENETDOWN ||
+                       error == EHOSTUNREACH || error == ENETUNREACH))
+        return mDNStrue;
+#ifdef __NetBSD__
+    if (multicast && error == EADDRNOTAVAIL) return mDNStrue;
+#endif
+    return mDNSfalse;
+}
+
 // mDNS core calls this routine when it needs to send a packet.
 mDNSexport mStatus mDNSPlatformSendUDP(const mDNS *const m, const void *const msg, const mDNSu8 *const end,
                                        mDNSInterfaceID InterfaceID, UDPSocket *src, const mDNSAddr *dst,
@@ -288,9 +299,9 @@
     else if (err < 0)
     {
         static int MessageCount = 0;
-        // Don't report EHOSTDOWN (i.e. ARP failure), ENETDOWN, or no route to host for unicast destinations
-        if (!mDNSAddressIsAllDNSLinkGroup(dst))
-            if (errno == EHOSTDOWN || errno == ENETDOWN || errno == EHOSTUNREACH || errno == ENETUNREACH) return(mStatus_TransientErr);
+        // Transient reachability errors should not be reported for packets still due for retry.
+        if (mDNSPosixShouldReturnTransientSendError(errno, mDNSAddressIsAllDNSLinkGroup(dst)))
+            return(mStatus_TransientErr);
 
         if (MessageCount < 1000)
         {
@@ -1488,6 +1499,20 @@
     return err;
 }
 
+mDNSlocal void mDNSPosixIgnoreIPv6SocketFailure(mStatus *error, int *socket)
+{
+#ifdef __NetBSD__
+    if (*error != mStatus_NoError)
+    {
+        *socket = -1;
+        *error = mStatus_NoError;
+    }
+#else
+    (void)error;
+    (void)socket;
+#endif
+}
+
 // Call get_ifi_info() to obtain a list of active interfaces and call SetupOneInterface() on each one.
 mDNSlocal int SetupInterfaceList(mDNS *const m)
 {
@@ -1996,7 +2021,11 @@
 #if HAVE_IPV6
     sa.sa_family = AF_INET6;
     m->p->unicastSocket6 = -1;
-    if (err == mStatus_NoError) err = SetupSocket(&sa, zeroIPPort, 0, &m->p->unicastSocket6);
+    if (err == mStatus_NoError)
+    {
+        err = SetupSocket(&sa, zeroIPPort, 0, &m->p->unicastSocket6);
+        mDNSPosixIgnoreIPv6SocketFailure(&err, &m->p->unicastSocket6);
+    }
 #endif
 
     // Tell mDNS core about the network interfaces on this machine.
