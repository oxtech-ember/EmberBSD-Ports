$NetBSD$

Remove the obsolete self-initialization warning workaround.
The oldstyle branch assigns saveprompt before the same branch restores it.
Do not read an indeterminate automatic variable at its declaration.
Origin: EmberBSD, AI-assisted; not submitted upstream.

--- src/parser.c.orig	2026-07-17 22:24:14.000000000 +0000
+++ src/parser.c
@@ -1521,7 +1521,7 @@ badsub:
  */
 
 parsebackq: {
-	int uninitialized_var(saveprompt);
+	int saveprompt;
 	struct heredoc *saveheredoclist;
 	struct nodelist **nlpp;
 	size_t savelen;
