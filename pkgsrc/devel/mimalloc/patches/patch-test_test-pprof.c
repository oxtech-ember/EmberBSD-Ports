$NetBSD$

Join threads only after pthread_create succeeds.
Origin: EmberBSD (AI-assisted).

--- test/test-pprof.c.orig
+++ test/test-pprof.c
@@ -618,9 +618,11 @@
 
       pthread_t threads[MI_TEST_PPROF_THREAD_COUNT];
       thread_arg_t args[MI_TEST_PPROF_THREAD_COUNT];
+      int created = 0;
       for (int t = 0; t < MI_TEST_PPROF_THREAD_COUNT && result; t++) {
         args[t].seed = (unsigned)(t + 1);
         result = (pthread_create(&threads[t], NULL, &thread_alloc_free_fun, &args[t]) == 0);
+        if (result) { created++; }
       }
 
       // take a few snapshots while the threads are still running
@@ -629,7 +631,7 @@
         mi_profiler_snapshot(prof);
       }
 
-      for (int t = 0; t < MI_TEST_PPROF_THREAD_COUNT; t++) {
+      for (int t = 0; t < created; t++) {
         pthread_join(threads[t], NULL);
       }
       thread_pool_cleanup();
