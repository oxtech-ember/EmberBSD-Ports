$NetBSD$

Print size_t and pointer-sized values with matching conversions.

--- tta/C/parsetexi/debug_parser.c.orig
+++ tta/C/parsetexi/debug_parser.c
@@ -123,7 +123,7 @@
       if (e->e.c->cmd)
         text_printf (&text, "@%s", debug_parser_command_name (e->e.c->cmd));
       if (e->e.c->contents.number)
-        text_printf (&text, "[C%d]", e->e.c->contents.number);
+        text_printf (&text, "[C%zu]", e->e.c->contents.number);
 
       if (print_parent && e->e.c->parent)
         {
