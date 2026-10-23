$NetBSD: patch-gio_tests_iptosmessage.c,v 1.1 2026/04/15 08:33:23 adam Exp $

Build each traffic-class test only when its socket option exists.
Unlike the older pkgsrc platform-wide skip, keep NetBSD's available IPv6
case testable while IP_RECVTOS is absent. Origin: EmberBSD (AI-assisted).

--- gio/tests/iptosmessage.c.orig
+++ gio/tests/iptosmessage.c
@@ -26,7 +26,7 @@
 
 /* See the g_test_skip() calls below for platform-specific reasons why this test
  * code sometimes needs to be skipped. */
-#if ! (defined(G_OS_WIN32) || defined(__APPLE__) || defined(__GNU__) || defined(_AIX) || defined(__sun__))
+#if ! (defined(G_OS_WIN32) || defined(__APPLE__) || defined(__GNU__) || defined(_AIX) || defined(__sun__)) && (defined(IP_RECVTOS) || defined(IPV6_RECVTCLASS))
 
 static GSocketControlMessage *
 send_recv_control_message (GSocketFamily family, GSocketControlMessage *msg)
@@ -69,11 +69,19 @@
 
   if (family == G_SOCKET_FAMILY_IPV4)
     {
+#ifdef IP_RECVTOS
       g_socket_set_option (rsock, IPPROTO_IP, IP_RECVTOS, 1, &error);
+#else
+      g_assert_not_reached ();
+#endif
     }
   else
     {
+#ifdef IPV6_RECVTCLASS
       g_socket_set_option (rsock, IPPROTO_IPV6, IPV6_RECVTCLASS, 1, &error);
+#else
+      g_assert_not_reached ();
+#endif
     }
   g_assert_no_error (error);
 
@@ -120,6 +128,8 @@
   g_test_skip ("IP_RECVTOS not supported on AIX");
 #elif defined(__sun__)
   g_test_skip ("IP_RECVTOS not supported on Solaris");
+#elif !defined(IP_RECVTOS)
+  g_test_skip ("IP_RECVTOS not supported on this platform");
 #else
   GIPTosMessage *smsg;
   GIPTosMessage *rmsg;
@@ -148,6 +158,8 @@
   g_test_skip ("IPV6_RECVTCLASS not supported on AIX");
 #elif defined(__sun__)
   g_test_skip ("IPV6_RECVTCLASS not supported on Solaris");
+#elif !defined(IPV6_RECVTCLASS)
+  g_test_skip ("IPV6_RECVTCLASS not supported on this platform");
 #else
   GIPv6TclassMessage *smsg;
   GIPv6TclassMessage *rmsg;
