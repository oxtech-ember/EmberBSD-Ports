$NetBSD$

Use a function prototype with C23 compilers. C23 removes K&R definitions.
Keep the System V math exception behavior and its platform guards.
AI-assisted EmberBSD adaptation; not submitted upstream.

--- src/libs/libgroff/matherr.c.orig
+++ src/libs/libgroff/matherr.c
@@ -26,8 +26,7 @@
 #ifdef HAVE_STRUCT_EXCEPTION
 #ifdef TLOSS
 
-int matherr(exc)
-struct exception *exc;
+int matherr(struct exception *exc)
 {
   switch (exc->type) {
   case SING:
