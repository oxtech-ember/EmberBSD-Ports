$NetBSD: patch-sntp_libevent_evutil__rand.c,v 1.1 2020/10/07 10:15:02 jperkin Exp $

Don't assume arc4random_addrandom() is available.

Rebased onto NTP 4.2.8p18 by EmberBSD (AI-assisted).

--- sntp/libevent/evutil_rand.c.orig
+++ sntp/libevent/evutil_rand.c
@@ -194,8 +194,10 @@
 void
 evutil_secure_rng_add_bytes(const char *buf, size_t n)
 {
+#ifndef __sun
 	arc4random_addrandom((unsigned char*)buf,
 	    n>(size_t)INT_MAX ? INT_MAX : (int)n);
+#endif
 }
 #endif
 
