$NetBSD$

Preserve 0.5.x callback ordinals for existing consumers; INS is appended.
This intentionally differs from upstream 0.6 binary enum values.
Origin: EmberBSD contributors (AI-assisted); not submitted upstream.

--- src/md4c.h.orig
+++ src/md4c.h
@@ -151,11 +151,6 @@
     /* <code>...</code> */
     MD_SPAN_CODE,
 
-    /* <ins>...</ins>
-     * Syntax: ++insert++
-     * Note: Recognized only when MD_FLAG_INSERT is enabled. */
-    MD_SPAN_INS,
-
     /* <del>...</del>
      * Note: Recognized only when MD_FLAG_STRIKETHROUGH is enabled.
      */
@@ -201,7 +196,13 @@
     /* <mark>...</mark>
      * Syntax: ==highlight==
      * Note: Recognized only when MD_FLAG_HIGHLIGHT is enabled. */
-    MD_SPAN_MARK
+    MD_SPAN_MARK,
+
+    /* <ins>...</ins>
+     * Syntax: ++insert++
+     * Note: Recognized only when MD_FLAG_INSERT is enabled. */
+    MD_SPAN_INS
+
 } MD_SPANTYPE;
 
 /* Text is the actual textual contents of span. */
