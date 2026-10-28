$NetBSD$

Allow freestanding consumers to supply their platform header glue.
Origin: EmberBSD (AI-assisted); upstream status: not submitted.

--- C/LzmaDec.c.orig
+++ C/LzmaDec.c
@@ -3,7 +3,9 @@
 
 #include "Precomp.h"
 
+#ifndef Z7_FREESTANDING
 #include <string.h>
+#endif
 
 /* #include "CpuArch.h" */
 #include "LzmaDec.h"
