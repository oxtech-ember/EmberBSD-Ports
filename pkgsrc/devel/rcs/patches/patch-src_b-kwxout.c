# Origin: EmberBSD (AI-assisted).
Preserve the configured local Id keyword in the common RCS source.

--- src/b-kwxout.c.orig
+++ src/b-kwxout.c
@@ -82,7 +82,7 @@
   RCSv = BE (version);
 
   if (exp != kwsub_v)
-    aprintf (out, "%c%s", KDELIM, marker->sym->bytes);
+    aprintf (out, "%c%s", KDELIM, marker->name);
   if (exp != kwsub_k)
     {
       if (exp != kwsub_v)
