$NetBSD$

Origin: EmberBSD (AI-assisted). Use the native LOCAL_PEEREID interface on the
NetBSD-compatible ABI. The old LOCAL_CREDS path calls a missing helper and
references an undefined fd; its ancillary buffer also omits supplementary groups.
The socket query returns the kernel-recorded peer PID and effective UID without
enabling ancillary credential delivery. Other platforms keep their existing path.

--- egg/egg-unix-credentials.c.orig
+++ egg/egg-unix-credentials.c
@@ -56,7 +56,7 @@
 	char buf;
 	int ret;
 	
-#if defined(HAVE_CMSGCRED) || defined(LOCAL_CREDS)
+#if (defined(HAVE_CMSGCRED) || defined(LOCAL_CREDS)) && !defined(__NetBSD__)
 	/* Prefer CMSGCRED over LOCAL_CREDS because the former provides the
 	 * remote PID. */
 #if defined(HAVE_CMSGCRED)
@@ -84,7 +84,7 @@
 	msg.msg_iov = &iov;
 	msg.msg_iovlen = 1;
 	
-#if defined(HAVE_CMSGCRED) || defined(LOCAL_CREDS)
+#if (defined(HAVE_CMSGCRED) || defined(LOCAL_CREDS)) && !defined(__NetBSD__)
 	memset (&cmsg, 0, sizeof (cmsg));
 	msg.msg_control = (caddr_t) &cmsg;
 	msg.msg_controllen = CMSG_SPACE(sizeof *cred);
@@ -108,7 +108,7 @@
 		return -1;
 	}
 
-#if defined(HAVE_CMSGCRED) || defined(LOCAL_CREDS)
+#if (defined(HAVE_CMSGCRED) || defined(LOCAL_CREDS)) && !defined(__NetBSD__)
 	if (cmsg.hdr.cmsg_len < CMSG_LEN (sizeof *cred) ||
 	    cmsg.hdr.cmsg_type != SCM_CREDS) {
 		fprintf (stderr, "message from recvmsg() was not SCM_CREDS\n");
@@ -117,7 +117,19 @@
 #endif
 
 	{
-#ifdef SO_PEERCRED
+#if defined(__NetBSD__)
+		struct unpcbid cr;
+		socklen_t cr_len = sizeof (cr);
+
+		if (getsockopt (sock, SOL_LOCAL, LOCAL_PEEREID, &cr, &cr_len) == 0 &&
+		    cr_len == sizeof (cr)) {
+			*pid = cr.unp_pid;
+			*uid = cr.unp_euid;
+		} else {
+			fprintf (stderr, "failed to get LOCAL_PEEREID credentials\n");
+			return -1;
+		}
+#elif defined(SO_PEERCRED)
 #ifndef __OpenBSD__
 		struct ucred cr;   
 #else
@@ -227,7 +239,7 @@
 egg_unix_credentials_setup (int sock)
 {
 	int retval = 0;
-#if defined(LOCAL_CREDS) && !defined(HAVE_CMSGCRED)
+#if defined(LOCAL_CREDS) && !defined(HAVE_CMSGCRED) && !defined(__NetBSD__)
 	int val = 1;
 	if (setsockopt (sock, 0, LOCAL_CREDS, &val, sizeof (val)) < 0) {
 		fprintf (stderr, "unable to set LOCAL_CREDS socket option on fd %d\n", fd);
