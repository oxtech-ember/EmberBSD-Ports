$NetBSD$

Origin: EmberBSD contributors (AI-assisted).
Run the selected XML validator with its original arguments and exit status.

--- src/meinproc_common.h.orig
+++ src/meinproc_common.h
@@ -15,7 +15,7 @@
 
 enum CheckResult {
     CheckSuccess,
-    CheckNoOut,
+    CheckFailed,
     CheckNoXmllint,
 };
 
