$NetBSD$

Keep accepting map option flags without storing the unused F flag.

Origin: EmberBSD (AI-assisted), diagnosed with Clang 23 and Binutils 2.47.
Not submitted upstream.

--- ld/ldlang.c.orig
+++ ld/ldlang.c
@@ -71,5 +71,4 @@
 static bool map_head_is_link_order = false;
 static lang_output_section_statement_type *default_common_section;
-static bool map_option_f;
 static bfd_vma print_dot;
 static lang_input_statement_type *first_file;
@@ -9094,7 +9094,6 @@ lang_add_map (const char *name)
       switch (*name)
 	{
 	case 'F':
-	  map_option_f = true;
 	  break;
 	}
       name++;
