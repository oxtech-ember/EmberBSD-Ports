$NetBSD$

Resolve the default dictionary from the loaded Netpbm shared library.
Explicit filename/RGBDEF and static builds preserve upstream behavior.
Origin: EmberBSD contributors (AI-assisted).

--- lib/colorname.c.orig
+++ lib/colorname.c
@@ -12,6 +12,8 @@
 ** implied warranty.
 */
 
+#define _GNU_SOURCE 1      /* Dl_info on glibc */
+#define _DARWIN_C_SOURCE 1 /* Dl_info with _XOPEN_SOURCE on Darwin */
 #define _DEFAULT_SOURCE 1  /* New name for SVID & BSD source defines */
 #define _BSD_SOURCE 1      /* Make sure strdup() is in string.h */
 #define _XOPEN_SOURCE 500  /* Make sure strdup() is in string.h */
@@ -22,6 +24,9 @@
 #include <stdlib.h>
 #include <errno.h>
 #include <math.h>
+#ifdef NETPBM_HAVE_DLADDR
+#include <dlfcn.h>
+#endif
 
 #include "netpbm/nstring.h"
 #include "netpbm/mallocvar.h"
@@ -85,6 +90,58 @@
 
 
 
+/* A private data address cannot resolve to a caller's PLT entry. */
+#ifdef NETPBM_HAVE_DLADDR
+static const char colornameLibraryAnchor;
+#endif
+
+static bool
+openColornameFileRelative(FILE ** const filePP) {
+/*----------------------------------------------------------------------------
+   Use the dictionary belonging to this loaded shared library, not one left
+   behind at its build prefix.  Return FALSE for static/unsupported images.
+   A recognized shared image returns TRUE even if its dictionary is missing.
+-----------------------------------------------------------------------------*/
+#ifdef NETPBM_HAVE_DLADDR
+    Dl_info image;
+    const char * base;
+    size_t length;
+    char * resolved;
+
+    *filePP = NULL;
+    if (!dladdr(&colornameLibraryAnchor, &image) || !image.dli_fname)
+        return FALSE;
+    base = strrchr(image.dli_fname, '/');
+    base = base ? base + 1 : image.dli_fname;
+    length = strlen(base);
+    if (!(strcmp(base, "libnetpbm.so") == 0 ||
+          strncmp(base, "libnetpbm.so.", sizeof("libnetpbm.so.") - 1) == 0 ||
+          (strncmp(base, "libnetpbm.", sizeof("libnetpbm.") - 1) == 0 &&
+           length >= sizeof("libnetpbm.dylib") - 1 &&
+           strcmp(base + length - 6, ".dylib") == 0)))
+        return FALSE;
+
+    resolved = realpath(image.dli_fname, NULL);
+    if (resolved) {
+        char * slash = strrchr(resolved, '/');
+        if (slash) {
+            const char * filename;
+            *slash = '\0';
+            pm_asprintf(&filename, "%s/../share/netpbm/rgb.txt", resolved);
+            if (filename != pm_strsol)
+                *filePP = fopen(filename, "r");
+            pm_strfree(filename);
+        }
+        free(resolved);
+    }
+    return TRUE;
+#else
+    return FALSE;
+#endif
+}
+
+
+
 FILE *
 pm_openColornameFile(const char * const fileName, const int must_open) {
 /*----------------------------------------------------------------------------
@@ -92,7 +149,8 @@
    'fileName' is NULL.  In that case, its file name is the value of the
    environment variable whose name is RGB_ENV (e.g. "RGBDEF").  Except
    if that environment variable is not set, it is the first file found,
-   if any, in the search path RGB_DB_PATH.
+   if any, beside the loaded shared library in ../share/netpbm/rgb.txt.
+   Static and unsupported images retain the search path RGB_DB_PATH.
 
    'must_open' is a logical: we must get the file open or die.  If
    'must_open' is true and we can't open the file (e.g. it doesn't
@@ -112,10 +170,9 @@
                          "errno = %d (%s)",
                          rgbdef, RGBENV, errno, strerror(errno));
         } else {
-            /* The environment variable isn't set, so try the hardcoded
-               default color name dictionary locations.
-            */
-            openColornameFileSearch(RGB_DB_PATH, &f);
+            bool const relative = openColornameFileRelative(&f);
+            if (!relative)
+                openColornameFileSearch(RGB_DB_PATH, &f);
 
             if (f == NULL && must_open) {
                 pm_error("can't open color names dictionary file from the "
@@ -123,7 +180,8 @@
                          "and Environment variable %s not set.  Set %s to "
                          "the pathname of your rgb.txt file or don't use "
                          "color names.",
-                         RGB_DB_PATH, RGBENV, RGBENV);
+                         relative ? "../share/netpbm/rgb.txt beside libnetpbm" :
+                             RGB_DB_PATH, RGBENV, RGBENV);
             }
         }
     } else {
