# Origin: EmberBSD (AI-assisted).
An empty linked list is a valid second argument to prepend.

--- src/b-esds.h.orig
+++ src/b-esds.h
@@ -40,10 +40,10 @@
 
 extern struct link *
 prepend (void const *x, struct link *ls, struct divvy *to)
-  ALL_NONNULL;
+  ARG_NONNULL ((1, 3));
 
 extern struct wlink *
 wprepend (void *x, struct wlink *ls, struct divvy *to)
-  ALL_NONNULL;
+  ARG_NONNULL ((1, 3));
 
 /* b-esds.h ends here */
