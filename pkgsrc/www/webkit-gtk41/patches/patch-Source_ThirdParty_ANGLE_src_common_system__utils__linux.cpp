$NetBSD$

Use CLOCK_MONOTONIC when CLOCK_MONOTONIC_RAW is unavailable on NetBSD.
Origin: EmberBSD (AI-assisted), for the pinned WebKitGTK 2.54.1 source.

--- Source/ThirdParty/ANGLE/src/common/system_utils_linux.cpp.orig
+++ Source/ThirdParty/ANGLE/src/common/system_utils_linux.cpp
@@ -51,14 +51,22 @@
 double GetCurrentSystemTime()
 {
     struct timespec currentTime;
+#if defined(CLOCK_MONOTONIC_RAW)
     clock_gettime(CLOCK_MONOTONIC_RAW, &currentTime);
+#else
+    clock_gettime(CLOCK_MONOTONIC, &currentTime);
+#endif
     return currentTime.tv_sec + currentTime.tv_nsec * 1e-9;
 }
 
 uint64_t GetCurrentSystemTimeNs()
 {
     struct timespec currentTime;
+#if defined(CLOCK_MONOTONIC_RAW)
     clock_gettime(CLOCK_MONOTONIC_RAW, &currentTime);
+#else
+    clock_gettime(CLOCK_MONOTONIC, &currentTime);
+#endif
     return static_cast<uint64_t>(currentTime.tv_sec) * 1000'000'000 + currentTime.tv_nsec;
 }
 
@@ -66,7 +74,10 @@
 {
     // There's a 15-character (16 including '\0') limit.  If the name is too big (and ERANGE is
     // returned), name will be ignored.
-    ASSERT(strlen(name) < 16);
+#ifdef __NetBSD__
+    pthread_setname_np(pthread_self(), "%s", (void *)name);
+#else
     pthread_setname_np(pthread_self(), name);
+#endif
 }
 }  // namespace angle
