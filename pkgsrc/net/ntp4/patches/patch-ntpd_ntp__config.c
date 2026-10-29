$NetBSD$

Retain the parser debug guard; keep upstream LOG_ERR for failed RLIMIT_MEMLOCK.
Origin: NetBSD pkgsrc; rebased by EmberBSD (AI-assisted). Upstream status: not submitted.

--- ntpd/ntp_config.c.orig
+++ ntpd/ntp_config.c
@@ -5198,7 +5198,7 @@
 	}
 
 	/*** BULK OF THE PARSER ***/
-#ifdef DEBUG
+#if defined(DEBUG) && defined(YYDEBUG)
 	yydebug = (debug >= 9);
 #endif
 	yyparse();
