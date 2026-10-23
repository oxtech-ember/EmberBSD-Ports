$NetBSD$

Keep the secure_getenv fallback private to its only translation unit.
The base library must not export a libc compatibility symbol.
Origin: upstream src/el.c 1.104; local EmberBSD Ports adaptation.
Prepared with AI assistance. Not submitted upstream.
Regression: tests/private-symbols.py, with the compiled library or el.o.

--- src/el.c.orig
+++ src/el.c
@@ -76,7 +76,8 @@
 #endif
 
 #ifndef HAVE_SECURE_GETENV
-char *secure_getenv(char const *name)
+static char *
+secure_getenv(char const *name)
 {
 	if (issetugid())
 		return 0;
