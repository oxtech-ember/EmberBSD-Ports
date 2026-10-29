$NetBSD$

Select parser and generated keyword table from the active build.
Origin: EmberBSD (AI-assisted). Upstream status: not submitted.

--- ntpd/ntp_scanner.c.orig
+++ ntpd/ntp_scanner.c
@@ -23,10 +23,10 @@
 #include "ntp_config.h"
 #include "ntpsim.h"
 #include "ntp_scanner.h"
-#include "ntp_parser.h"
+#include <ntp_parser.h>
 
 /* ntp_keyword.h declares finite state machine and token text */
-#include "ntp_keyword.h"
+#include <ntp_keyword.h>
 
 
 
