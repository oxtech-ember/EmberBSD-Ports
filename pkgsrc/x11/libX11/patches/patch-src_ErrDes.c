$NetBSD$

Preserve prefix-owned default paths when the native package is moved.
Origin: EmberBSD contributors (AI-assisted); not submitted upstream.

--- src/ErrDes.c.orig
+++ src/ErrDes.c
@@ -52,6 +52,8 @@
 #include <config.h>
 #endif
 #include "Xlibint.h"
+#include <X11/XlibRelocate.h>
+static const char x11_relocation_anchor;
 #include <X11/Xos.h>
 #include "Xresource.h"
 #include <stdio.h>
@@ -160,6 +162,7 @@
 	XrmDatabase temp_db;
 	int do_destroy;
 	const char *dbname;
+        char *relocated = NULL;
 
 	XrmInitialize();
 #ifdef WIN32
@@ -167,9 +170,11 @@
 	if (!dbname)
 	    dbname = ERRORDB;
 #else
-    dbname = ERRORDB;
+    relocated = _x11_relocated_path (&x11_relocation_anchor, "libX11", X11_RELOC_PREFIX, X11_RELOC_LIBDIR, ERRORDB);
+    dbname = relocated ? relocated : ERRORDB;
 #endif
 	temp_db = XrmGetFileDatabase(dbname);
+        free(relocated);
 
 	_XLockMutex(_Xglobal_lock);
 	if (!db) {
