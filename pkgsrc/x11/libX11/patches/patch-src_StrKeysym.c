$NetBSD$

Preserve prefix-owned default paths when the native package is moved.
Origin: EmberBSD contributors (AI-assisted); not submitted upstream.

--- src/StrKeysym.c.orig
+++ src/StrKeysym.c
@@ -29,6 +29,8 @@
 #endif
 #include <limits.h>
 #include "Xlibint.h"
+#include <X11/XlibRelocate.h>
+static const char x11_relocation_anchor;
 #include <X11/Xresource.h>
 #include <X11/keysymdef.h>
 #include "Xresinternal.h"
@@ -55,14 +57,18 @@
     if (!initialized)
     {
 	const char *dbname;
+        char *relocated = NULL;
 
 	XrmInitialize();
 	/* use and name of this env var is not part of the standard */
 	/* implementation-dependent feature */
 	dbname = getenv("XKEYSYMDB");
-	if (!dbname)
-	    dbname = KEYSYMDB;
+	if (!dbname) {
+            relocated = _x11_relocated_path (&x11_relocation_anchor, "libX11", X11_RELOC_PREFIX, X11_RELOC_LIBDIR, KEYSYMDB);
+	    dbname = relocated ? relocated : KEYSYMDB;
+        }
 	keysymdb = XrmGetFileDatabase(dbname);
+        free(relocated);
 	if (keysymdb)
 	    Qkeysym[0] = XrmStringToQuark("Keysym");
 	initialized = True;
