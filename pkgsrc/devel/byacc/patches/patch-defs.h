$NetBSD$

Preserve NetBSD and EmberBSD byacc integration changes from the OS source.
Origin: NetBSD and EmberBSD (AI-assisted); not submitted upstream.

--- defs.h.orig
+++ defs.h
@@ -1,4 +1,8 @@
 /* $Id: defs.h,v 1.76 2026/01/24 13:46:31 tom Exp $ */
+
+#if HAVE_NBTOOL_CONFIG_H
+#include "nbtool_config.h"
+#endif
 
 #ifdef HAVE_CONFIG_H
 #include <config.h>
