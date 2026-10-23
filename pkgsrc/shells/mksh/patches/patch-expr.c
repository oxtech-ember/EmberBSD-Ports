$NetBSD$

Do not read an arithmetic result when evaluation returns an error.
The recoverable KSH_RETURN_ERROR path does not initialize v.val.i.
Keep the caller's output unchanged, as callers test the status first.
Origin: EmberBSD, AI-assisted; not submitted upstream.

--- expr.c.orig
+++ expr.c
@@ -110,7 +110,8 @@
 	v.flag = DEFINED | INTEGER;
 	v.type = 0;
 	ret = v_evaluate(&v, expr, error_ok, arith);
-	*rval = v.val.i;
+	if (ret)
+		*rval = v.val.i;
 	return (ret);
 }
 
