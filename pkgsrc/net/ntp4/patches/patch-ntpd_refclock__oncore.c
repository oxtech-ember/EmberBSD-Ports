$NetBSD$

Retain NetBSD receiver formatting buffer sizes for a 16-bit sigma value.
The obsolete p15 brace hunks are not carried: p18 clarifies both scopes.
Origin: NetBSD pkgsrc; rebased by EmberBSD (AI-assisted).
Upstream status: not submitted.

--- ntpd/refclock_oncore.c.orig
+++ ntpd/refclock_oncore.c
@@ -1806,7 +1806,7 @@
 		Rsm = ((instance->BEHa[129]<<8) | instance->BEHa[130]);
 
 	if (instance->chan == 6 || instance->chan == 8) {
-		char	f1[5], f2[5], f3[5], f4[5];
+		char	f1[6], f2[6], f3[6], f4[6];
 		if (instance->traim) {
 			snprintf(f1, sizeof(f1), "%d",
 				 instance->BEHn[21]);
@@ -1839,7 +1839,7 @@
 		    instance->BEHa[57], instance->BEHa[61], instance->BEHa[65], instance->BEHa[69]
 		    );					/* will be 0 for 6 chan */
 	} else if (instance->chan == 12) {
-		char	f1[5], f2[5], f3[5], f4[5];
+		char	f1[6], f2[6], f3[6], f4[6];
 		if (instance->traim) {
 			snprintf(f1, sizeof(f1), "%d",
 				 instance->BEHn[6]);
