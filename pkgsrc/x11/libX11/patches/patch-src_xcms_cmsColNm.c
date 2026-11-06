$NetBSD$

Preserve prefix-owned default paths when the native package is moved.
Origin: EmberBSD contributors (AI-assisted); not submitted upstream.

--- src/xcms/cmsColNm.c.orig
+++ src/xcms/cmsColNm.c
@@ -35,6 +35,8 @@
 #include <config.h>
 #endif
 #include "Xlibint.h"
+#include <X11/XlibRelocate.h>
+static const char x11_relocation_anchor;
 #include "Xcmsint.h"
 #include <X11/Xos.h>
 #include <sys/stat.h>
@@ -735,28 +737,34 @@
     int size;
     FILE *stream;
     const char *pathname;
+    char *relocated = NULL;
     struct stat txt;
     int length;
 
     /* use and name of this env var is not part of the standard */
     /* implementation-dependent feature */
     if ((pathname = getenv("XCMSDB")) == NULL) {
-	pathname = XCMSDB;
+        relocated = _x11_relocated_path (&x11_relocation_anchor, "libX11", X11_RELOC_PREFIX, X11_RELOC_LIBDIR, XCMSDB);
+	pathname = relocated ? relocated : XCMSDB;
     }
 
     length = (int)strlen(pathname);
     if ((length == 0) || (length >= (BUFSIZ - 5))){
+        free(relocated);
 	XcmsColorDbState = XcmsDbInitFailure;
 	return(XcmsFailure);
     }
 
     if (stat(pathname, &txt)) {
+        free(relocated);
 	/* can't stat file */
 	XcmsColorDbState = XcmsDbInitFailure;
 	return(XcmsFailure);
     }
 
-    if ((stream = _XFopenFile (pathname, "r")) == NULL) {
+    stream = _XFopenFile (pathname, "r");
+    free(relocated);
+    if (stream == NULL) {
 	/* can't open file */
 	XcmsColorDbState = XcmsDbInitFailure;
 	return(XcmsFailure);
