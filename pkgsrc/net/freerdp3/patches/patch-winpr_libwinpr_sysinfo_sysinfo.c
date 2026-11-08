$NetBSD$

Use CLOCK_MONOTONIC and HW_NCPU on NetBSD.

--- winpr/libwinpr/sysinfo/sysinfo.c.orig
+++ winpr/libwinpr/sysinfo/sysinfo.c
@@ -37,6 +37,9 @@
 #if !defined(_WIN32)
 #if defined(_POSIX_C_SOURCE) && (_POSIX_C_SOURCE >= 199309L)
 #include <time.h>
+#elif defined(__NetBSD__)
+#include <sys/time.h>
+#include <time.h>
 #elif !defined(__APPLE__)
 #include <sys/time.h>
 #include <sys/sysinfo.h>
@@ -175,7 +178,7 @@
 		int mib[4];
 		size_t length = sizeof(numCPUs);
 		mib[0] = CTL_HW;
-#if defined(__FreeBSD__) || defined(__OpenBSD__)
+#if defined(__FreeBSD__) || defined(__OpenBSD__) || defined(__NetBSD__)
 		mib[1] = HW_NCPU;
 #else
 		mib[1] = HW_AVAILCPU;
@@ -580,6 +583,10 @@
 		ticks = (ts.tv_sec * 1000000000ull) + ts.tv_nsec;
 #elif defined(__MACH__) && defined(__APPLE__)
 	ticks = mac_get_time_ns();
+#elif defined(__NetBSD__)
+	struct timespec ts = { 0 };
+	if (clock_gettime(CLOCK_MONOTONIC, &ts) == 0)
+		ticks = (ts.tv_sec * 1000000000ull) + ts.tv_nsec;
 #elif defined(_WIN32)
 	LARGE_INTEGER li = { 0 };
 	LARGE_INTEGER freq = { 0 };
