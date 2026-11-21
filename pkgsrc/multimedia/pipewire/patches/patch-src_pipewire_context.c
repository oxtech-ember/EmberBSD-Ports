$NetBSD$

NetBSD does not define RLIMIT_LOCKS, RLIMIT_MSGQUEUE, RLIMIT_NICE,
RLIMIT_RTPRIO, RLIMIT_RTTIME or RLIMIT_SIGPENDING; skip the optional
table entries there.

Enable mutex priority inheritance by default only when the target supports it.
An explicitly configured loop can still request the protocol.

--- src/pipewire/context.c.orig
+++ src/pipewire/context.c
@@ -195,10 +195,16 @@
 static int setup_data_loops(struct impl *impl)
 {
 	struct pw_properties *pr;
+	const char *prio_inherit = "true";
 	struct pw_context *this = &impl->this;
 	const char *str, *lib_name;
 	uint32_t i;
 	int res = 0;
+
+#ifdef _SC_THREAD_PRIO_INHERIT
+	if (sysconf(_SC_THREAD_PRIO_INHERIT) <= 0)
+		prio_inherit = "false";
+#endif
 
 	pr = pw_properties_copy(this->properties);
 
@@ -230,7 +236,7 @@
 			pw_properties_clear(pr);
 			pw_properties_update(pr, &this->properties->dict);
 			pw_properties_set(pr, PW_KEY_LIBRARY_NAME_SYSTEM, lib_name);
-			pw_properties_set(pr, "loop.prio-inherit",  "true");
+			pw_properties_set(pr, "loop.prio-inherit", prio_inherit);
 
 			while ((l = spa_json_object_next(&it[1], key, sizeof(key), &val)) > 0) {
 				if (spa_json_is_container(val, l))
@@ -263,7 +269,7 @@
 		}
 		for (i = 0; i < impl->n_data_loops; i++) {
 			pw_properties_setf(pr, SPA_KEY_THREAD_NAME,  "data-loop.%d", i);
-			pw_properties_set(pr, "loop.prio-inherit",  "true");
+			pw_properties_set(pr, "loop.prio-inherit", prio_inherit);
 			impl->data_loops[i].impl = pw_data_loop_new(&pr->dict);
 			if (impl->data_loops[i].impl == NULL)  {
 				res = -errno;
@@ -351,16 +357,28 @@
 		[RLIMIT_CPU]        = "cpu",
 		[RLIMIT_DATA]       = "data",
 		[RLIMIT_FSIZE]      = "fsize",
+#ifdef RLIMIT_LOCKS
 		[RLIMIT_LOCKS]      = "locks",
+#endif
 		[RLIMIT_MEMLOCK]    = "memlock",
+#ifdef RLIMIT_MSGQUEUE
 		[RLIMIT_MSGQUEUE]   = "msgqueue",
+#endif
+#ifdef RLIMIT_NICE
 		[RLIMIT_NICE]       = "nice",
+#endif
 		[RLIMIT_NOFILE]     = "nofile",
 		[RLIMIT_NPROC]      = "nproc",
 		[RLIMIT_RSS]        = "rss",
+#ifdef RLIMIT_RTPRIO
 		[RLIMIT_RTPRIO]     = "rtprio",
+#endif
+#ifdef RLIMIT_RTTIME
 		[RLIMIT_RTTIME]     = "rttime",
+#endif
+#ifdef RLIMIT_SIGPENDING
 		[RLIMIT_SIGPENDING] = "sigpending",
+#endif
 		[RLIMIT_STACK]      = "stack",
 	};
 	int res;
