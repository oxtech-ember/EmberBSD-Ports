$NetBSD$

Allow the source consumer to select its regex match type.
Origin: EmberBSD contributors (AI-assisted).

--- xdiff/xdiffi.c.orig
+++ xdiff/xdiffi.c
@@ -1046,7 +1046,7 @@
 }
 
 static int record_matches_regex(xrecord_t *rec, xpparam_t const *xpp) {
-	regmatch_t regmatch;
+	XDL_REGMATCH_TYPE regmatch;
 	size_t i;
 
 	for (i = 0; i < xpp->ignore_regex_nr; i++)
