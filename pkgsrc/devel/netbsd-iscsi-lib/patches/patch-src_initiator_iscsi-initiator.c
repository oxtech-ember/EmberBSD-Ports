Remove write-only counter; preserve -v debug selection.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- src/initiator/iscsi-initiator.c.orig
+++ src/initiator/iscsi-initiator.c
@@ -52,7 +52,6 @@
 
 #include "defs.h"
 
-static int		 verbose; /* how chatty are we? */
 
 static virtdir_t	 iscsi;
 
@@ -605,7 +604,6 @@
 			exit(EXIT_SUCCESS);
 			/* NOTREACHED */
 		case 'v':
-			verbose += 1;
 			if (strcmp(optarg, "net") == 0) {
 				iscsi_initiator_setvar(&ini, "debug", "net");
 			} else if (strcmp(optarg, "iscsi") == 0) {
