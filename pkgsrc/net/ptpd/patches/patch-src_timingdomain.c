$NetBSD$

Write the kernel NTP state (status, error estimates, TAI offset, leap
second flags) only from a slave that may adjust the clock. A master,
a passive port or clock:no_adjust leaves it to the clock owner, such
as chronyd.

--- src/timingdomain.c.orig
+++ src/timingdomain.c
@@ -414,6 +414,17 @@
 		return 0;
 	}
 
+	/*
+	 * The kernel NTP state (status, error estimates, TAI offset and
+	 * leap second flags) belongs to the process that disciplines the
+	 * clock. A master, a passive port or a port with clock:no_adjust
+	 * does not discipline it, so the update stays pending until this
+	 * port is a slave that may adjust the clock.
+	 */
+	if(rtOpts->noAdjust || ptpClock->portDS.portState != PTP_SLAVE) {
+		return 0;
+	}
+
 	DBG_LOCAL_ID(service, "clock status update\n");
 
 #if defined(MOD_TAI) &&  NTP_API == 4
