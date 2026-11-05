Origin: EmberBSD; AI-assisted, not submitted upstream.
Use the probed locale APIs and a numeric C locale on all supporting hosts.
Prevent process LC_NUMERIC from changing GLSL numeric constants.
--- src/util/strtod.c.orig
+++ src/util/strtod.c
@@ -24,11 +24,15 @@
  */
 
 
+#if defined(HAVE_STRTOD_L) && !defined(_GNU_SOURCE)
+#define _GNU_SOURCE 1
+#endif
+
 #include "util/u_atexit.h"
 
 #include <stdlib.h>
 
-#if defined(_GNU_SOURCE) && defined(HAVE_STRTOD_L)
+#if defined(HAVE_STRTOD_L)
 #include <locale.h>
 #ifdef HAVE_XLOCALE_H
 #include <xlocale.h>
@@ -38,7 +42,7 @@
 #include "strtod.h"
 #include "util/u_call_once.h"
 
-#if defined(_GNU_SOURCE) && defined(HAVE_STRTOD_L)
+#if defined(HAVE_STRTOD_L)
 
 static locale_t loc;
 
@@ -51,7 +55,9 @@
 static void
 _mesa_locale_init_once(void)
 {
-   loc = newlocale(LC_CTYPE_MASK, "C", NULL);
+   loc = newlocale(LC_CTYPE_MASK | LC_NUMERIC_MASK, "C", NULL);
+   if (!loc)
+      abort();
    util_atexit(_mesa_locale_fini);
 }
 
@@ -72,7 +78,7 @@
 double
 _mesa_strtod(const char *s, char **end)
 {
-#if defined(_GNU_SOURCE) && defined(HAVE_STRTOD_L)
+#if defined(HAVE_STRTOD_L)
    return strtod_l(s, end, _mesa_get_locale());
 #else
    return strtod(s, end);
@@ -87,7 +93,7 @@
 float
 _mesa_strtof(const char *s, char **end)
 {
-#if defined(_GNU_SOURCE) && defined(HAVE_STRTOD_L)
+#if defined(HAVE_STRTOD_L)
    return strtof_l(s, end, _mesa_get_locale());
 #elif defined(HAVE_STRTOF)
    return strtof(s, end);
