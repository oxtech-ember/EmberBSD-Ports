$NetBSD$

NetBSD regex(3) does not define the macOS-only REG_ENHANCED flag.
Guard it so the enhanced-atoms fallback compiles; without the flag
those atoms match literally on NetBSD.

--- compat/regcomp_enhanced.c.orig	2026-10-12 00:00:00.000000000 +0000
+++ compat/regcomp_enhanced.c
@@ -8,6 +8,13 @@
 	 * https://lore.kernel.org/git/458ad3c1-96df-4575-ee42-e6eb754f25f6@gmx.de/
 	 * might be relevant.
 	 */
+#ifndef REG_ENHANCED
+/*
+ * NetBSD's regex(3) has no REG_ENHANCED extension (macOS only); the
+ * enhanced atoms degrade to literal matching there.
+ */
+#define REG_ENHANCED 0
+#endif
 	if (!(cflags & REG_EXTENDED))
 		cflags |= REG_ENHANCED;
 	return regcomp(preg, pattern, cflags);

