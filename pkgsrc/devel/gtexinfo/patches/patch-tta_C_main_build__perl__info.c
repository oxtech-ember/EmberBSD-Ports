$NetBSD$

Print size_t and pointer-sized values with matching conversions.

--- tta/C/main/build_perl_info.c.orig
+++ tta/C/main/build_perl_info.c
@@ -236,7 +236,7 @@
               char *debug_str = print_element_debug (element, 1);
               text_init (&message);
               text_printf (&message,
-                "BUG: build_perl_array oot %d: %s\n", i, debug_str);
+                "BUG: build_perl_array oot %zu: %s\n", i, debug_str);
               non_perl_free (debug_str);
               fprintf (stderr, "%s", message.text);
               non_perl_free (message.text);
@@ -280,7 +280,7 @@
               char *debug_str = print_element_debug (f, 1);
               text_init (&message);
               text_printf (&message,
-                "BUG: build_perl_const_element_array oot %d: %s\n", i, debug_str);
+                "BUG: build_perl_const_element_array oot %zu: %s\n", i, debug_str);
               non_perl_free (debug_str);
               fprintf (stderr, "%s", message.text);
               non_perl_free (message.text);
