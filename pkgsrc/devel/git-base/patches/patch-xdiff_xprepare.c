$NetBSD$

Avoid pointer arithmetic on NULL when an xdiff allocation fails.
Origin: EmberBSD contributors (AI-assisted).

--- xdiff/xprepare.c.orig
+++ xdiff/xprepare.c
@@ -134,7 +134,8 @@
 static void xdl_free_ctx(xdfile_t *xdf)
 {
 	xdl_free(xdf->reference_index);
-	xdl_free(xdf->changed - 1);
+	if (xdf->changed != NULL)
+		xdl_free(xdf->changed - 1);
 	xdl_free(xdf->recs);
 }
 
