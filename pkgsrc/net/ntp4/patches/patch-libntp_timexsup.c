$NetBSD: patch-libntp_timexsup.c,v 1.1 2020/06/21 15:10:47 taca Exp $

* Changes from NetBSD base.

Rebased onto NTP 4.2.8p18 by EmberBSD (AI-assisted).

--- libntp/timexsup.c.orig
+++ libntp/timexsup.c
@@ -17,6 +17,7 @@
 # endif
 #endif
 #ifdef HAVE_SYS_TIMEX_H
+# include <time.h>
 # include <sys/timex.h>
 #else
 # ifdef HAVE_TIMEX_H
