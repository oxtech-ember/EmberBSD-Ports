$NetBSD$

Keep distinct optimized pprof allocation frames and only join threads whose
creation succeeded. Preserve failed-create test failure without invalid joins.
Origin: EmberBSD (AI-assisted).

--- test/test-pprof.c.orig
+++ test/test-pprof.c
@@ -72,8 +72,18 @@
 // fewer distinct ones (or even just one).
 static void* volatile mi_test_pprof_sink;
 
+// The sink prevents tail calls, but each allocation site also needs its own
+// frame when Release optimization would otherwise inline these functions.
+#if defined(_MSC_VER)
+#define MI_TEST_NOINLINE __declspec(noinline)
+#elif defined(__GNUC__)
+#define MI_TEST_NOINLINE __attribute__((noinline))
+#else
+#define MI_TEST_NOINLINE
+#endif
+
 #define MI_TEST_PPROF_DEFINE_SITE(N) \
-  static void* alloc_site_##N(size_t block_size, size_t i) { \
+  static MI_TEST_NOINLINE void* alloc_site_##N(size_t block_size, size_t i) { \
     void* p = mi_malloc(block_size + (i % 37)); \
     mi_test_pprof_sink = p; \
     return p; \
@@ -553,9 +563,11 @@
 
       pthread_t threads[MI_TEST_PPROF_THREAD_COUNT];
       thread_arg_t args[MI_TEST_PPROF_THREAD_COUNT];
+      int created = 0;
       for (int t = 0; t < MI_TEST_PPROF_THREAD_COUNT && result; t++) {
         args[t].seed = (unsigned)(t + 1);
         result = (pthread_create(&threads[t], NULL, &thread_alloc_free_fun, &args[t]) == 0);
+        if (result) { created++; }
       }
 
       // take a few snapshots while the threads are still running
@@ -564,7 +576,7 @@
         mi_profiler_snapshot(prof);
       }
 
-      for (int t = 0; t < MI_TEST_PPROF_THREAD_COUNT; t++) {
+      for (int t = 0; t < created; t++) {
         pthread_join(threads[t], NULL);
       }
       thread_pool_cleanup();
