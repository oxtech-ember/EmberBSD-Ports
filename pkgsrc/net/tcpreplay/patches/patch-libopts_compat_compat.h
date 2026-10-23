$NetBSD$

The bundled libopts compatibility header falls back to defining an enum
with false/true when stdbool.h was not detected. false and true are
keywords in C++ and in C23, so the fallback must not be used there.

--- libopts/compat/compat.h.orig	2023-09-02 16:07:44.000000000 +0000
+++ libopts/compat/compat.h
@@ -184,7 +184,7 @@
 
 #if defined(HAVE_STDBOOL_H)
 #  include <stdbool.h>
-#elif ! defined(bool)
+#elif ! defined(bool) && ! defined(__cplusplus) && (! defined(__STDC_VERSION__) || __STDC_VERSION__ < 202311L)
    typedef enum { false = 0, true = 1 } _Bool;
 #  define bool _Bool
 
