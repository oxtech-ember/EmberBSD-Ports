$NetBSD$

The base MetaBackend type is only pulled in transitively by the native
and X11 backend headers; include the public header directly so the
barrier manager compiles without either backend. Origin: EmberBSD (AI-assisted).

--- src/backends/meta-barrier.c	2026-09-15 17:26:39.000000000 +0300
+++ src/backends/meta-barrier.c	2026-10-14 11:16:40.816130746 +0300
@@ -10,6 +10,7 @@
 
 #include "meta/barrier.h"
 #include "backends/meta-barrier-private.h"
+#include "meta/meta-backend.h"
 
 #include <glib-object.h>
 
