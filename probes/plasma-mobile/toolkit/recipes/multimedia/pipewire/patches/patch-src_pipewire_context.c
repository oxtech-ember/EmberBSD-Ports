$NetBSD$

NetBSD does not define RLIMIT_LOCKS, RLIMIT_MSGQUEUE, RLIMIT_NICE,
RLIMIT_RTPRIO, RLIMIT_RTTIME or RLIMIT_SIGPENDING; skip the optional
table entries there.

--- src/pipewire/context.c.orig	2026-10-13
+++ src/pipewire/context.c
@@ -351,16 +351,28 @@
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
