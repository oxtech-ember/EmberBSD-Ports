$NetBSD$

Allow consumers to preserve allocation and error policy; Git defaults are unchanged.
The empty-allocation option affects only unchanged-side fast paths; the general
xdl_do_merge path retains its normal allocator behavior.
Origin: EmberBSD contributors (AI-assisted).

--- xdiff/xmerge.c.orig
+++ xdiff/xmerge.c
@@ -88,7 +88,7 @@
 		if (c->mode == 0)
 			count++;
 		next_c = c->next;
-		free(c);
+		xdl_free(c);
 	}
 	return count;
 }
@@ -456,7 +456,7 @@
 	m->chg1 = next_m->i1 + next_m->chg1 - m->i1;
 	m->chg2 = next_m->i2 + next_m->chg2 - m->i2;
 	m->next = next_m->next;
-	free(next_m);
+	xdl_free(next_m);
 }
 
 /*
@@ -709,18 +709,28 @@
 		goto out;
 
 	if (!xscr1) {
-		result->ptr = xdl_malloc(mf2->size);
-		if (!result->ptr)
-			goto out;
+		if (mf2->size || XDL_MERGE_ALLOC_EMPTY) {
+			result->ptr = xdl_malloc(mf2->size);
+			if (!result->ptr)
+				goto out;
+		} else {
+			result->ptr = NULL;
+		}
 		status = 0;
-		memcpy(result->ptr, mf2->ptr, mf2->size);
+		if (mf2->size)
+			memcpy(result->ptr, mf2->ptr, mf2->size);
 		result->size = mf2->size;
 	} else if (!xscr2) {
-		result->ptr = xdl_malloc(mf1->size);
-		if (!result->ptr)
-			goto out;
+		if (mf1->size || XDL_MERGE_ALLOC_EMPTY) {
+			result->ptr = xdl_malloc(mf1->size);
+			if (!result->ptr)
+				goto out;
+		} else {
+			result->ptr = NULL;
+		}
 		status = 0;
-		memcpy(result->ptr, mf1->ptr, mf1->size);
+		if (mf1->size)
+			memcpy(result->ptr, mf1->ptr, mf1->size);
 		result->size = mf1->size;
 	} else {
 		status = xdl_do_merge(&xe1, xscr1,
