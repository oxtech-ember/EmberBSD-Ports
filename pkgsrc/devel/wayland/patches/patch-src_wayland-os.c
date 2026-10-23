$NetBSD: patch-src_wayland-os.c,v 1.4 2022/08/04 15:21:26 nia Exp $

Support for NetBSD. EmberBSD (AI-assisted) corrects peer identification:
LOCAL_CREDS is an integer control-message option, not struct sockcred output.
LOCAL_PEEREID returns the peer PID and effective IDs in struct unpcbid.
See https://man.netbsd.org/unix.4 . Not yet submitted upstream.

--- src/wayland-os.c.orig	2022-06-30 21:59:11.000000000 +0000
+++ src/wayland-os.c
@@ -100,6 +100,24 @@ wl_os_socket_peercred(int sockfd, uid_t 
 #endif
 	return 0;
 }
+#elif defined(__NetBSD__)
+#ifndef SOL_LOCAL
+#define SOL_LOCAL (0)
+#endif
+int
+wl_os_socket_peercred(int sockfd, uid_t *uid, gid_t *gid, pid_t *pid)
+{
+	socklen_t len;
+	struct unpcbid ucred;
+
+	len = sizeof(ucred);
+	if (getsockopt(sockfd, SOL_LOCAL, LOCAL_PEEREID, &ucred, &len) < 0)
+		return -1;
+	*uid = ucred.unp_euid;
+	*gid = ucred.unp_egid;
+	*pid = ucred.unp_pid;
+	return 0;
+}
 #elif defined(SO_PEERCRED)
 int
 wl_os_socket_peercred(int sockfd, uid_t *uid, gid_t *gid, pid_t *pid)
