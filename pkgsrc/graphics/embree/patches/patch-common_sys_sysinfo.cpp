$NetBSD$

Origin: EmberBSD contributors (AI-assisted).
Count dynamic NetBSD affinity without assuming dense CPU IDs.
--- common/sys/sysinfo.cpp
+++ common/sys/sysinfo.cpp
@@ -11,6 +11,11 @@
 #include "intrinsics.h"
 #include "estring.h"
 #include "ref.h"
+#if defined(__NetBSD__)
+#include <climits>
+#include <limits>
+#include <sched.h>
+#endif
 #if defined(__FREEBSD__)
 #include <sys/cpuset.h>
 #include <pthread_np.h>
@@ -668,7 +673,31 @@
     static int nThreads = -1;
     if (nThreads != -1) return nThreads;
 
-#if defined(__MACOSX__) || defined(__ANDROID__)
+#if defined(__NetBSD__)
+    cpuset_t* set = cpuset_create();
+    int count = 0;
+    if (set) {
+      const size_t bytes = cpuset_size(set);
+      if (bytes > 0 && bytes <= SIZE_MAX / CHAR_BIT &&
+          bytes * CHAR_BIT - 1 <= std::numeric_limits<cpuid_t>::max() &&
+          pthread_getaffinity_np(pthread_self(), bytes, set) == 0) {
+        for (size_t cpu = 0; cpu < bytes * CHAR_BIT; ++cpu) {
+          const int present = cpuset_isset(cpu, set);
+          if (present < 0 || (present && count == INT_MAX)) {
+            count = 0;
+            break;
+          }
+          count += present != 0;
+        }
+      }
+      cpuset_destroy(set);
+    }
+    if (count == 0) {
+      const long online = sysconf(_SC_NPROCESSORS_ONLN);
+      count = online > 0 && online <= INT_MAX ? int(online) : 1;
+    }
+    nThreads = count;
+#elif defined(__MACOSX__) || defined(__ANDROID__)
     nThreads = sysconf(_SC_NPROCESSORS_ONLN); // does not work in Linux LXC container
     assert(nThreads);
 #elif defined(__EMSCRIPTEN__)
