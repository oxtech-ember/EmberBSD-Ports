$NetBSD$

Preserve prefix-owned default paths when the native package is moved.
Origin: EmberBSD contributors (AI-assisted); not submitted upstream.

--- src/xlibi18n/lcFile.c.orig
+++ src/xlibi18n/lcFile.c
@@ -30,6 +30,8 @@
 #include <stdio.h>
 #include <ctype.h>
 #include "Xlibint.h"
+#include <X11/XlibRelocate.h>
+static const char x11_relocation_anchor;
 #include "XlcPubI.h"
 #include <X11/Xos.h>
 #include <unistd.h>
@@ -225,8 +227,11 @@
     }
 #endif /* NO_XLOCALEDIR */
 
-    if (len < buf_len)
-      strncpy(p, XLOCALEDIR, (size_t) (buf_len - len));
+    if (len < buf_len) {
+      char *relocated = _x11_relocated_path (&x11_relocation_anchor, "libX11", X11_RELOC_PREFIX, X11_RELOC_LIBDIR, XLOCALEDIR);
+      strncpy(p, relocated ? relocated : XLOCALEDIR, (size_t) (buf_len - len));
+      free(relocated);
+    }
     buf[buf_len-1] = '\0';
 }
 
@@ -299,8 +304,11 @@
     }
 #endif /* NO_XLOCALEDIR */
 
-    if (len < buf_len)
-      strncpy(p, XLOCALELIBDIR, (size_t) (buf_len - len));
+    if (len < buf_len) {
+      char *relocated = _x11_relocated_path (&x11_relocation_anchor, "libX11", X11_RELOC_PREFIX, X11_RELOC_LIBDIR, XLOCALELIBDIR);
+      strncpy(p, relocated ? relocated : XLOCALELIBDIR, (size_t) (buf_len - len));
+      free(relocated);
+    }
     buf[buf_len-1] = '\0';
 }
 
