$NetBSD$

Allow source consumers to supply compatible allocation and policy hooks;
keep the Git defaults unchanged. Origin: EmberBSD contributors (AI-assisted).

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
