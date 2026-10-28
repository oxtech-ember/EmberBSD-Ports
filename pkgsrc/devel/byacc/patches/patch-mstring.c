$NetBSD$

Preserve NetBSD and EmberBSD byacc integration changes from the OS source.
Origin: NetBSD and EmberBSD (AI-assisted); not submitted upstream.

--- mstring.c.orig
+++ mstring.c
@@ -1,4 +1,8 @@
 /* $Id: mstring.c,v 1.11 2024/12/14 16:48:04 tom Exp $ */
+
+#if HAVE_NBTOOL_CONFIG_H
+#include "nbtool_config.h"
+#endif
 
 #include <stdlib.h>
 #include <stdio.h>
