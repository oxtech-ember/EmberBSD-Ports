$NetBSD$

Keep the old allocation in its Area if resizing fails or overflows.
internal_errorf may unwind to an interactive shell, so Area cleanup must
still own the caller's old object. Save its successor before realloc can
move the object; do not read the old storage after successful realloc.
Origin: EmberBSD, AI-assisted; not submitted upstream.

--- lalloc.c.orig
+++ lalloc.c
@@ -140,14 +140,12 @@
 void *
 aresize(void *ptr, size_t numb, Area *ap)
 {
-	struct lalloc_common *lp = NULL;
+	struct lalloc_common *lp = NULL, *pp = NULL, *next = NULL;
 
 	/* resizing (true) or newly allocating? */
 	if (ptr != NULL) {
-		struct lalloc_common *pp;
-
 		pp = findptr(&lp, ptr, ap);
-		pp->next = lp->next;
+		next = lp->next;
 	}
 
 	if (notoktoadd(numb, sizeof(ALLOC_ITEM)) ||
@@ -157,6 +155,9 @@
 #endif
 	    )
 		internal_errorf(Toomem, numb);
+	/* Keep the old item linked until remalloc succeeds. */
+	if (pp != NULL)
+		pp->next = next;
 	/* area pointer and items share struct lalloc_common */
 	lp->next = ap->next;
 	ap->next = lp;
