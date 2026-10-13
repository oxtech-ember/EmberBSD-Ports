$NetBSD$

Release trap strings when clearing inherited traps and after EXIT handlers.
Keep the EXIT action pointer unchanged across setjmp so cleanup also runs
when the handler exits or raises a shell error.
Origin: EmberBSD, AI-assisted; not submitted upstream.

--- src/trap.c.orig
+++ src/trap.c
@@ -186,7 +186,7 @@
 			if (simplecmd)
 				*tp = otp;
 			else
-				ckfree(*tp);
+				ckfree(otp);
 		}
 	}
 	trapcnt = 0;
@@ -409,14 +409,14 @@
 exitshell(void)
 {
 	struct jmploc loc;
-	char *p;
+	char *p = trap[0];
 
 	savestatus = exitstatus;
 	TRACE(("pid %d, exitshell(%d)\n", getpid(), savestatus));
 	if (setjmp(loc.loc))
 		goto out;
 	handler = &loc;
-	if ((p = trap[0])) {
+	if (p) {
 		trap[0] = NULL;
 		if (ptrap)
 			goto out;
@@ -425,6 +425,7 @@
 		evalskip = SKIPFUNCDEF;
 	}
 out:
+	ckfree(p);
 	exitreset();
 	postexitreset();
 	/*
