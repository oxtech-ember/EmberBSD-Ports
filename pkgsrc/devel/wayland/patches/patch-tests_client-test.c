Origin: EmberBSD (AI-assisted). Verify real peer PID and effective IDs.
Not yet submitted upstream.

--- tests/client-test.c.orig
+++ tests/client-test.c
@@ -205,3 +205,32 @@
 
 	wl_display_destroy(display);
 }
+
+#if defined(__NetBSD__)
+/* Origin: EmberBSD (AI-assisted); LOCAL_CREDS is not peer identification. */
+TEST(client_peer_credentials)
+{
+	struct wl_display *display;
+	struct wl_client *client;
+	uid_t uid = (uid_t)-1;
+	gid_t gid = (gid_t)-1;
+	pid_t pid = -1;
+	int s[2];
+
+	assert(socketpair(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0, s) == 0);
+	display = wl_display_create();
+	assert(display);
+	client = wl_client_create(display, s[0]);
+	assert(client);
+	wl_client_get_credentials(client, &pid, &uid, &gid);
+	fprintf(stderr, "peer pid=%ld uid=%ld gid=%ld; expected %ld %ld %ld\n",
+		(long)pid, (long)uid, (long)gid,
+		(long)getpid(), (long)geteuid(), (long)getegid());
+	assert(pid == getpid());
+	assert(uid == geteuid());
+	assert(gid == getegid());
+	wl_client_destroy(client);
+	close(s[1]);
+	wl_display_destroy(display);
+}
+#endif
