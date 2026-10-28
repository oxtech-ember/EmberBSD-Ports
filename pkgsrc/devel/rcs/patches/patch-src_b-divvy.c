# Origin: EmberBSD (AI-assisted).
Clang requires the obstack handler function pointer to carry noreturn.
The adapter preserves the existing allocation-failure behavior.

--- src/b-divvy.c.orig
+++ src/b-divvy.c
@@ -26,6 +26,12 @@
 #include "b-complain.h"
 #include "b-divvy.h"
 
+static __attribute_noreturn__ void
+rcs_obstack_alloc_failed (void)
+{
+  xalloc_die ();
+}
+
 struct divvy *plexus;
 struct divvy *single;
 
@@ -40,7 +46,7 @@
   struct divvy *divvy = TMALLOC (struct divvy);
 
   divvy->name = name;
-  obstack_alloc_failed_handler = xalloc_die;
+  obstack_alloc_failed_handler = rcs_obstack_alloc_failed;
   obstack_init (&divvy->space);
 
   /* Set alignment to avoid segfault (on some hosts).
