# Origin: EmberBSD (AI-assisted).
Accept the optional state identifier specified by the RCS file grammar.

--- src/b-grok.c.orig
+++ src/b-grok.c
@@ -709,7 +709,8 @@
         SEMI (g, author);
 
         SYNCH (g, state);
-        MUST_SNIPPET (g, state);
+        /* The state identifier is optional in the RCS file grammar.  */
+        (void) maybe_read_snippet (g);
         STASH (d->state);
         SEMI (g, state);
 
