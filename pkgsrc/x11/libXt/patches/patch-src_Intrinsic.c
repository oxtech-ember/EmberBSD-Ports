$NetBSD$

Preserve prefix-owned default paths when the native package is moved.
Origin: EmberBSD contributors (AI-assisted); not submitted upstream.

--- src/Intrinsic.c.orig
+++ src/Intrinsic.c
@@ -74,6 +74,9 @@
 #include <config.h>
 #endif
 #include "IntrinsicI.h"
+#include <X11/XlibRelocate.h>
+#include <stdint.h>
+static const char xt_relocation_anchor;
 #include "VarargsI.h"           /* for geoTattler */
 #ifndef NO_IDENTIFY_WINDOWS
 #include <X11/Xatom.h>
@@ -1328,6 +1331,43 @@
 }
 
 
+/* Only the implementation default is relocated; environment paths are literal. */
+static char *
+implementation_relocated_path(const char *input)
+{
+    const char *start = input, *end;
+    char *out = NULL;
+    size_t used = 0;
+    do {
+        size_t n, partlen;
+        char *part, *relocated, *next;
+        end = start;
+        while (*end && *end != ':') {
+            if (end[0] == '%' && end[1] != '\0') end++;
+            end++;
+        }
+        n = (size_t)(end - start);
+        part = malloc(n + 1);
+        if (!part) { free(out); return NULL; }
+        memcpy(part, start, n); part[n] = '\0';
+        relocated = _x11_relocated_path (&xt_relocation_anchor, "libXt",
+                                          X11_RELOC_PREFIX, X11_RELOC_LIBDIR, part);
+        partlen = strlen(relocated ? relocated : part);
+        if (partlen > SIZE_MAX - used - 2) { free(relocated); free(part); free(out); return NULL; }
+        next = realloc(out, used + partlen + 2);
+        if (!next) { free(relocated); free(part); free(out); return NULL; }
+        out = next;
+        memcpy(out + used, relocated ? relocated : part, partlen);
+        used += partlen;
+        free(relocated); free(part);
+        if (*end) out[used++] = ':';
+        out[used] = '\0';
+        start = *end ? end + 1 : end;
+    } while (*end);
+    return out;
+}
+
+
 /* *INDENT-OFF* */
 static SubstitutionRec defaultSubs[] = {
     {'N', NULL},
@@ -1353,7 +1393,9 @@
 {
     XtPerDisplay pd;
     static const char *defaultPath = NULL;
-    const char *impl_default = implementation_default_path();
+    static Boolean defaultPathInitialized = False;
+    char *owned_default = implementation_relocated_path(implementation_default_path());
+    const char *impl_default = owned_default ? owned_default : implementation_default_path();
     int idef_len = (int) strlen(impl_default);
     char *massagedPath;
     int bytesAllocd, bytesLeft;
@@ -1368,12 +1410,11 @@
     LOCK_PROCESS;
     pd = _XtGetPerDisplay(dpy);
     if (path == NULL) {
-        if (defaultPath == NULL) {
+        if (!defaultPathInitialized) {
             defaultPath = getenv("XFILESEARCHPATH");
-            if (defaultPath == NULL)
-                defaultPath = impl_default;
-        }
-        path = defaultPath;
+            defaultPathInitialized = True;
+        }
+        path = defaultPath ? defaultPath : impl_default;
     }
 
     if (path == NULL)
@@ -1495,6 +1536,7 @@
         DEALLOCATE_LOCAL(massagedPath);
 
     UNLOCK_PROCESS;
+    free(owned_default);
     return result;
 }
 
