$NetBSD$

Allow source consumers to supply compatible allocation and policy hooks;
keep the Git defaults unchanged. Origin: EmberBSD contributors (AI-assisted).

--- xdiff/xinclude.h.orig
+++ xdiff/xinclude.h
@@ -23,7 +23,11 @@
 #if !defined(XINCLUDE_H)
 #define XINCLUDE_H
 
+#ifdef XDL_COMPAT_HEADER
+#include XDL_COMPAT_HEADER
+#else
 #include "git-compat-util.h"
+#endif
 #include "xmacros.h"
 #include "xdiff.h"
 #include "xtypes.h"
