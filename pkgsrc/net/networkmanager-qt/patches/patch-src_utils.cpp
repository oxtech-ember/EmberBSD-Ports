$NetBSD$

Start the boot-time clock probe at CLOCK_MONOTONIC on NetBSD;
there is no CLOCK_BOOTTIME to probe first, and the function
already falls back to the monotonic clock.
Origin: EmberBSD (AI-assisted), not submitted upstream.

--- src/utils.cpp.orig
+++ src/utils.cpp
@@ -599,7 +599,13 @@
 
 QDateTime NetworkManager::clockBootTimeToDateTime(qlonglong clockBootime)
 {
+#if defined(Q_OS_NETBSD)
+    // NetBSD has no CLOCK_BOOTTIME; the fallback CLOCK_MONOTONIC branch
+    // below is the only usable clock, so start there.
+    clockid_t clk_id = CLOCK_MONOTONIC;
+#else
     clockid_t clk_id = CLOCK_BOOTTIME;
+#endif
     struct timespec tp;
     int r;
 
