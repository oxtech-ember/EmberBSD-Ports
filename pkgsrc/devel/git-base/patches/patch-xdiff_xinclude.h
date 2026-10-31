$NetBSD$

Allow consumers to report invariant errors while Git keeps its BUG policy.
Origin: EmberBSD contributors (AI-assisted).

--- xdiff/xinclude.h.orig
+++ xdiff/xinclude.h
@@ -23,7 +23,16 @@
 #if !defined(XINCLUDE_H)
 #define XINCLUDE_H
 
+#ifdef XDL_COMPAT_HEADER
+#include XDL_COMPAT_HEADER
+#else
 #include "git-compat-util.h"
+#endif
+#ifndef XDL_REPORT_BUG
+#define XDL_REPORT_BUG(...) BUG(__VA_ARGS__)
+#endif
+#define XDL_RETURN_BUG(...) do { XDL_REPORT_BUG(__VA_ARGS__); return -1; } while (0)
+
 #include "xmacros.h"
 #include "xdiff.h"
 #include "xtypes.h"
