$NetBSD$

Preserve prefix-owned default paths when the native package is moved.
Origin: EmberBSD contributors (AI-assisted); not submitted upstream.

--- src/Error.c.orig
+++ src/Error.c
@@ -72,6 +72,8 @@
 #include <config.h>
 #endif
 #include "IntrinsicI.h"
+#include <X11/XlibRelocate.h>
+static const char xt_relocation_anchor;
 #include <stdio.h>
 #include <stdlib.h>
 
@@ -231,7 +233,9 @@
 {
     XrmDatabase errordb;
 
-    errordb = XrmGetFileDatabase(ERRORDB);
+    char *relocated = _x11_relocated_path (&xt_relocation_anchor, "libXt", X11_RELOC_PREFIX, X11_RELOC_LIBDIR, ERRORDB);
+    errordb = XrmGetFileDatabase(relocated ? relocated : ERRORDB);
+    free(relocated);
     XrmMergeDatabases(errordb, db);
 }
 
