$NetBSD: patch-ntpd_refclock__jupiter.c,v 1.1 2020/06/21 15:10:47 taca Exp $

* Changes from NetBSD base.

Rebased onto NTP 4.2.8p18 by EmberBSD (AI-assisted).

--- ntpd/refclock_jupiter.c.orig
+++ ntpd/refclock_jupiter.c
@@ -186,8 +186,8 @@
 	snprintf(gpsdev, sizeof(gpsdev), DEVICE, unit);
 	fd = refclock_open(&peer->srcadr, gpsdev, SPEED232, LDISC_RAW);
 	if (fd <= 0) {
-		jupiter_debug(peer, "jupiter_start", "open %s: %m",
-			      gpsdev);
+		jupiter_debug(peer, "jupiter_start", "open %s: %s",
+			      gpsdev, strerror(errno));
 		return (0);
 	}
 
