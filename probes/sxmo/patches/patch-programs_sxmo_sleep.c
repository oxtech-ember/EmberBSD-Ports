$NetBSD$

Origin: EmberBSD (AI-assisted).
Use only clocks that the target timerfd API defines.
Reject unavailable alarm and boottime clocks with a clear error.
Keep the Linux clocks and the normal timerfd path.

--- programs/sxmo_sleep.c.orig
+++ programs/sxmo_sleep.c
@@ -3,6 +3,7 @@
 #include <stdio.h>       // dprintf
 #include <stdlib.h>      // strtol, exit
 #include <string.h>      // strerror, strcmp
+#include <time.h>
 #include <sys/timerfd.h> // timers
 #include <unistd.h>      // read
 
@@ -38,11 +39,23 @@
 			} else if (0 == strcmp(argv[i+1], "monotonic")) {
 				clockid = CLOCK_MONOTONIC;
 			} else if (0 == strcmp(argv[i+1], "boottime")) {
+#ifdef CLOCK_BOOTTIME
 				clockid = CLOCK_BOOTTIME;
+#else
+				usage(argv[0], "Clock boottime is not supported on this platform.");
+#endif
 			} else if (0 == strcmp(argv[i+1], "realtime_alarm")) {
+#ifdef CLOCK_REALTIME_ALARM
 				clockid = CLOCK_REALTIME_ALARM;
+#else
+				usage(argv[0], "Clock realtime_alarm is not supported on this platform.");
+#endif
 			} else if (0 == strcmp(argv[i+1], "boottime_alarm")) {
+#ifdef CLOCK_BOOTTIME_ALARM
 				clockid = CLOCK_BOOTTIME_ALARM;
+#else
+				usage(argv[0], "Clock boottime_alarm is not supported on this platform.");
+#endif
 			} else {
 				usage(argv[0], "Unknown clock name.");
 			}
