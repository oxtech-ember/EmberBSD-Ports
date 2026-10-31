$NetBSD$

Allow consumers to report invariant errors while Git keeps its BUG policy.
Origin: EmberBSD contributors (AI-assisted).

--- xdiff/xemit.c.orig
+++ xdiff/xemit.c
@@ -50,10 +50,14 @@
 	long max_ignorable;
 	long ignored = 0; /* number of ignored blank lines */
 
-	if (xecfg->ctxlen < 0)
-		BUG("negative context length: %ld", xecfg->ctxlen);
-	if (xecfg->interhunkctxlen < 0)
-		BUG("negative inter-hunk context length: %ld", xecfg->interhunkctxlen);
+	if (xecfg->ctxlen < 0) {
+		XDL_REPORT_BUG("negative context length: %ld", xecfg->ctxlen);
+		return NULL;
+	}
+	if (xecfg->interhunkctxlen < 0) {
+		XDL_REPORT_BUG("negative inter-hunk context length: %ld", xecfg->interhunkctxlen);
+		return NULL;
+	}
 
 	max_common = saturating_add(saturating_add(xecfg->ctxlen,
 						   xecfg->ctxlen),
@@ -176,6 +180,8 @@
 	for (xch = xscr; xch; xch = xche->next) {
 		xdchange_t *xchp = xch;
 		xche = xdl_get_hunk(&xch, xecfg);
+		if (xch && !xche)
+			return -1;
 		if (!xch)
 			break;
 
