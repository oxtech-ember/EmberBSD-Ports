$NetBSD$

Keep the MRI truncate command hook, but remove its value storage. The value
has no consumer in this linker.

Origin: EmberBSD (AI-assisted), diagnosed with Clang 23 and Binutils 2.47.
Not submitted upstream.

--- ld/mri.c.orig
+++ ld/mri.c
@@ -45,7 +45,6 @@ struct section_name_struct {
   int ok_to_load;
 };

-static unsigned int symbol_truncate = 10000;
 static etree_type *base; /* Relocation base - or null */

 static struct section_name_struct *order;
@@ -312,5 +311,5 @@ mri_alignmod (const char *name, etree_type *exp)
 void
 mri_truncate (unsigned int exp)
 {
-  symbol_truncate = exp;
+  (void) exp;
 }
