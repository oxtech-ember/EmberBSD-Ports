$NetBSD$

Origin: EmberBSD contributors (AI-assisted).
Use NetBSD dynamic cpuset API for thread affinity.
--- common/sys/thread.cpp
+++ common/sys/thread.cpp
@@ -296,6 +296,27 @@
 #endif
 
 ////////////////////////////////////////////////////////////////////////////////
+/// NetBSD Platform
+////////////////////////////////////////////////////////////////////////////////
+
+#if defined(__NetBSD__)
+#include <sched.h>
+
+namespace embree
+{
+  void setAffinity(ssize_t affinity)
+  {
+    if (affinity < 0) return;
+    cpuset_t* set = cpuset_create();
+    if (!set) return;
+    if (cpuset_set(static_cast<cpuid_t>(affinity), set) == 0)
+      pthread_setaffinity_np(pthread_self(), cpuset_size(set), set);
+    cpuset_destroy(set);
+  }
+}
+#endif
+
+////////////////////////////////////////////////////////////////////////////////
 /// WebAssembly Platform
 ////////////////////////////////////////////////////////////////////////////////
 
