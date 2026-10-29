$NetBSD$

Keep shared resolver state only for the threaded worker implementation.
Origin: EmberBSD (AI-assisted). Upstream status: not submitted.

--- libntp/ntp_intres.c.orig
+++ libntp/ntp_intres.c
@@ -191,5 +191,5 @@ dnsworker_ctx **	dnsworker_contexts;		/* child */
 u_int			dnsworker_contexts_alloc;
 
-#ifdef HAVE_RES_INIT
+#if defined(HAVE_RES_INIT) && defined(WORK_THREAD)
 static	time_t		next_res_init;
 #endif
@@ -1029,5 +1029,7 @@ worker_sleep_until(
 #ifdef HAVE_RES_INIT
 			worker_ctx->next_res_init = now + 60;
+#ifdef WORK_THREAD
 			next_res_init = worker_ctx->next_res_init;
+#endif
 			res_init();
 #endif
