$NetBSD$

Preserve prefix-owned default paths when the native package is moved.
Origin: EmberBSD contributors (AI-assisted); not submitted upstream.

--- src/xlibi18n/lcDynamic.c.orig
+++ src/xlibi18n/lcDynamic.c
@@ -48,6 +48,8 @@
 #include <dlfcn.h>
 
 #include "Xlibint.h"
+#include <X11/XlibRelocate.h>
+static const char x11_relocation_anchor;
 #include "Xlcint.h"
 
 #ifndef XLOCALEDIR
@@ -64,9 +66,12 @@
     XLCdMethods _XlcGenericMethods;
     XLCd lcd;
     void *nlshandler;
+    char *relocated = _x11_relocated_path (&x11_relocation_anchor, "libX11",
+                                            X11_RELOC_PREFIX, X11_RELOC_LIBDIR, XLOCALEDIR);
 
     snprintf(libpath, sizeof(libpath), "%s/%s/%s",
-	     XLOCALEDIR, name, LCLIBNAME);
+	     relocated ? relocated : XLOCALEDIR, name, LCLIBNAME);
+    free(relocated);
     nlshandler = dlopen(libpath,LAZY);
     _XlcGenericMethods = (XLCdMethods)dlsym(nlshandler,"genericMethods");
     lcd = _XlcCreateLC(name,_XlcGenericMethods);
