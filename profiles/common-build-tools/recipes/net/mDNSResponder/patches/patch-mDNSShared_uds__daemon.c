$NetBSD: patch-mDNSShared_uds__daemon.c,v 1.2 2024/11/20 17:56:21 hauke Exp $

Include required for OpenBSD 5.5

MAX() defined, but not in scope, so do it here

Origin: EmberBSD (AI-assisted), adapt the original pkgsrc patch to 2881.120.11.

The published request_state has no resolve_awdl field or AWDLInterfaceID.
Keep both resolver event logs and their public values; omit the private-only operand.

Stop socket setup if F_GETFL fails. Close a newly created listening socket
on startup failure, retaining caller-owned launch sockets.

--- mDNSShared/uds_daemon.c.orig
+++ mDNSShared/uds_daemon.c
@@ -24,6 +24,7 @@
 #include <sys/types.h>
 #include <sys/time.h>
 #include <sys/resource.h>
+#include <sys/uio.h>
 #include <sys/param.h>
 #endif
 
@@ -129,6 +130,11 @@
 #else
 #define NORETURN_ATTRIBUTE
 #endif
+#endif
+
+/* From dns_common.h */
+#ifndef MAX
+#define MAX(A, B) (((A) > (B)) ? (A) : (B))
 #endif
 
 //======================================================================================================================
@@ -3626,7 +3632,6 @@
     request_state *const req = question->QuestionContext;
     const mDNSu32 name_hash = mDNS_DomainNameFNV1aHash(&question->qname);
     const mDNSBool isMDNSQuestion = mDNSOpaque16IsZero(question->TargetQID);
-    const mDNSBool is_split_awdl_query = (req->resolve_awdl && question->InterfaceID == AWDLInterfaceID);
     UDS_LOG_ANSWER_EVENT(isMDNSQuestion ? MDNS_LOG_CATEGORY_MDNS : MDNS_LOG_CATEGORY_DEFAULT, MDNS_LOG_DEFAULT,
         req, question, answer, mDNSfalse, "DNSServiceResolve result", AddRecord);
 
@@ -3713,18 +3718,18 @@
     {
         LogRedact(MDNS_LOG_CATEGORY_DEFAULT, MDNS_LOG_DEFAULT, "[R%u->(Q%u, Q%u)] DNSServiceResolve RESULT -- "
             "instance: " PRI_DM_NAME "(" PRI_HEX_INT "), ifindex: %u, target host: " PRI_DM_NAME "(" PRI_HEX_INT
-            "), port: %u, negative txt: " PUB_BOOL ", txt rdlength: %u, split AWDL query: " PUB_BOOL,
+            "), port: %u, negative txt: " PUB_BOOL ", txt rdlength: %u",
             req->request_id, mDNSVal16(resolve->qsrv.TargetQID), mDNSVal16(resolve->qtxt.TargetQID),
             DM_NAME_PARAM_NONNULL(answer->name), name_hash, interface_index,
             DM_NAME_PARAM_NONNULL(resolve->srv_target_name), target_name_hash, mDNSVal16(srv_port),
-            BOOL_PARAM(resolve->txt_negative), txt_rdlength, BOOL_PARAM(is_split_awdl_query));
+            BOOL_PARAM(resolve->txt_negative), txt_rdlength);
     }
     else
     {
         LogRedact(MDNS_LOG_CATEGORY_DEFAULT, MDNS_LOG_DEFAULT, "[R%u->(Q%u, Q%u)] DNSServiceResolve NoSuchRecord -- "
-            "instance: " PRI_DM_NAME "(" PRI_HEX_INT "), split AWDL query: " PUB_BOOL,
+            "instance: " PRI_DM_NAME "(" PRI_HEX_INT ")",
             req->request_id, mDNSVal16(resolve->qsrv.TargetQID), mDNSVal16(resolve->qtxt.TargetQID),
-            DM_NAME_PARAM_NONNULL(answer->name), name_hash, BOOL_PARAM(is_split_awdl_query));
+            DM_NAME_PARAM_NONNULL(answer->name), name_hash);
     }
     append_reply(req, rep);
 }
@@ -5067,7 +5072,8 @@
     u_long opt = 1;
     if (ioctlsocket(skt, FIONBIO, &opt) != 0)
 #else
-    if (fcntl(skt, F_SETFL, fcntl(skt, F_GETFL, 0) | O_NONBLOCK) != 0)
+    const int flags = fcntl(skt, F_GETFL, 0);
+    if (flags == -1 || fcntl(skt, F_SETFL, flags | O_NONBLOCK) != 0)
 #endif
     {
         my_perror("ERROR: could not set listen socket to non-blocking mode");
@@ -5245,6 +5251,11 @@
 error:
 
     my_perror("ERROR: udsserver_init");
+    if (!skts && dnssd_SocketValid(listenfd))
+    {
+        dnssd_close(listenfd);
+        listenfd = dnssd_InvalidSocket;
+    }
     return -1;
 }
 
