$NetBSD$

Allow consumers to report invariant errors while Git keeps its BUG policy.
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
 
@@ -191,7 +192,7 @@
 }
 
 
-static bool xdl_clean_mmatch(uint8_t const *action, ptrdiff_t i, ptrdiff_t len) {
+static int xdl_clean_mmatch(uint8_t const *action, ptrdiff_t i, ptrdiff_t len) {
 	ptrdiff_t r, rdis0, rpdis0, rdis1, rpdis1;
 	ptrdiff_t s = 0, e = len - 1;
 
@@ -222,7 +223,7 @@
 		else if (action[i - r] == KEEP)
 			break;
 		else
-			BUG("Illegal value for action[i - r]");
+			XDL_RETURN_BUG("Illegal value for action[i - r]");
 	}
 	/*
 	 * If the run before the line 'i' found only multimatch lines,
@@ -241,7 +242,7 @@
 		else if (action[i + r] == KEEP)
 			break;
 		else
-			BUG("Illegal value for action[i + r]");
+			XDL_RETURN_BUG("Illegal value for action[i + r]");
 	}
 	/*
 	 * If the run after the line 'i' found only multimatch lines,
@@ -337,7 +338,12 @@
 		uint8_t action = action1[i];
 
 		if (action == INVESTIGATE) {
-			if (!xdl_clean_mmatch(action1, i, len1))
+			int clean = xdl_clean_mmatch(action1, i, len1);
+			if (clean < 0) {
+				ret = -1;
+				goto cleanup;
+			}
+			if (!clean)
 				action = KEEP;
 			else
 				action = DISCARD;
@@ -349,7 +355,9 @@
 		} else if (action == DISCARD) {
 			xdf1->changed[i + off] = true;
 		} else {
-			BUG("Illegal state for action");
+			XDL_REPORT_BUG("Illegal state for action");
+			ret = -1;
+			goto cleanup;
 		}
 	}
 
@@ -358,7 +366,12 @@
 		uint8_t action = action2[i];
 
 		if (action == INVESTIGATE) {
-			if (!xdl_clean_mmatch(action2, i, len2))
+			int clean = xdl_clean_mmatch(action2, i, len2);
+			if (clean < 0) {
+				ret = -1;
+				goto cleanup;
+			}
+			if (!clean)
 				action = KEEP;
 			else
 				action = DISCARD;
@@ -370,7 +383,9 @@
 		} else if (action == DISCARD) {
 			xdf2->changed[i + off] = true;
 		} else {
-			BUG("Illegal state for action");
+			XDL_REPORT_BUG("Illegal state for action");
+			ret = -1;
+			goto cleanup;
 		}
 	}
 
