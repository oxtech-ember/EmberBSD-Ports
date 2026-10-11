$NetBSD$

The autoopts options header has the same false/true enum fallback as
the compat header; the keywords exist in C++ and C23.

--- libopts/autoopts/options.h.orig	2023-09-02 16:07:44.000000000 +0000
+++ libopts/autoopts/options.h
@@ -64,7 +64,7 @@
 
 #  if defined(HAVE_STDBOOL_H)
 #    include <stdbool.h>
-#  elif ! defined(bool)
+#  elif ! defined(bool) && ! defined(__cplusplus) && (! defined(__STDC_VERSION__) || __STDC_VERSION__ < 202311L)
      typedef enum { false = 0, true = 1 } _Bool;
 #    define bool _Bool
 
