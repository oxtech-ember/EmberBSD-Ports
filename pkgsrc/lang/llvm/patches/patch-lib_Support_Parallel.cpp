$NetBSD$

Origin: EmberBSD (AI-assisted), LLVM 23.1.4 native parallel links.
Wait for the worker to return from the last latch unlock before the
calling thread can reuse its storage on NetBSD. Keep the public ABI and
the configured worker count. Not submitted upstream.
SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

--- lib/Support/Parallel.cpp.orig
+++ lib/Support/Parallel.cpp
@@ -96,11 +96,21 @@
     static void call(void *Ptr) { ((ThreadPoolExecutor *)Ptr)->stop(); }
   };
 
+#ifdef __NetBSD__
+  // NetBSD libpthread may still access a mutex while returning from unlock.
+  // Pair the worker's final latch access with the group's destruction so the
+  // stack containing that mutex can be reused only after unlock has returned.
+  std::mutex CompletionMutex;
+#endif
+
   struct WorkItem {
     std::function<void()> F;
     std::reference_wrapper<parallel::detail::Latch> L;
-    void operator()() {
+    void operator()(ThreadPoolExecutor &Executor) {
       F();
+#ifdef __NetBSD__
+      std::lock_guard<std::mutex> Lock(Executor.CompletionMutex);
+#endif
       L.get().dec();
     }
   };
@@ -134,7 +144,7 @@
     auto Item = std::move(WorkStack.back());
     WorkStack.pop_back();
     Lock.unlock();
-    Item();
+    Item(*this);
   }
 
   void work(ThreadPoolStrategy S, unsigned ThreadID) {
@@ -245,6 +255,11 @@
     getDefaultExecutor()->helpSync(L);
 #endif
   L.sync();
+#if LLVM_ENABLE_THREADS && defined(__NetBSD__)
+  if (Parallel) {
+    std::lock_guard<std::mutex> Lock(getDefaultExecutor()->CompletionMutex);
+  }
+#endif
 }
 
 void TaskGroup::spawn(std::function<void()> F) {
