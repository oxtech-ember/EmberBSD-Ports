$NetBSD$

Allow consumers to report invariant errors while Git keeps its BUG policy.
Origin: EmberBSD contributors (AI-assisted).

--- xdiff/xdiffi.c.orig
+++ xdiff/xdiffi.c
@@ -827,7 +827,7 @@
 			/* Shift the group backward as much as possible: */
 			while (!group_slide_up(xdf, &g))
 				if (group_previous(xdfo, &go))
-					BUG("group sync broken sliding up");
+					XDL_RETURN_BUG("group sync broken sliding up");
 
 			/*
 			 * This is this highest that this group can be shifted.
@@ -843,7 +843,7 @@
 				if (group_slide_down(xdf, &g))
 					break;
 				if (group_next(xdfo, &go))
-					BUG("group sync broken sliding down");
+					XDL_RETURN_BUG("group sync broken sliding down");
 
 				if (go.end > go.start)
 					end_matching_other = g.end;
@@ -869,9 +869,9 @@
 			 */
 			while (go.end == go.start) {
 				if (group_slide_up(xdf, &g))
-					BUG("match disappeared");
+					XDL_RETURN_BUG("match disappeared");
 				if (group_previous(xdfo, &go))
-					BUG("group sync broken sliding to match");
+					XDL_RETURN_BUG("group sync broken sliding to match");
 			}
 		} else if (flags & XDF_INDENT_HEURISTIC) {
 			/*
@@ -912,9 +912,9 @@
 
 			while (g.end > best_shift) {
 				if (group_slide_up(xdf, &g))
-					BUG("best shift unreached");
+					XDL_RETURN_BUG("best shift unreached");
 				if (group_previous(xdfo, &go))
-					BUG("group sync broken sliding to blank line");
+					XDL_RETURN_BUG("group sync broken sliding to blank line");
 			}
 		}
 
@@ -962,11 +962,11 @@
 		if (group_next(xdf, &g))
 			break;
 		if (group_next(xdfo, &go))
-			BUG("group sync broken moving to next group");
+			XDL_RETURN_BUG("group sync broken moving to next group");
 	}
 
 	if (!group_next(xdfo, &go))
-		BUG("group sync broken at end of file");
+		XDL_RETURN_BUG("group sync broken at end of file");
 
 	return 0;
 }
@@ -1014,6 +1014,8 @@
 
 	for (xch = xscr; xch; xch = xche->next) {
 		xche = xdl_get_hunk(&xch, xecfg);
+		if (xch && !xche)
+			return -1;
 		if (!xch)
 			break;
 		if (xecfg->hunk_func(xch->i1, xche->i1 + xche->chg1 - xch->i1,
@@ -1046,7 +1048,7 @@
 }
 
 static int record_matches_regex(xrecord_t *rec, xpparam_t const *xpp) {
-	regmatch_t regmatch;
+	XDL_REGMATCH_TYPE regmatch;
 	size_t i;
 
 	for (i = 0; i < xpp->ignore_regex_nr; i++)
