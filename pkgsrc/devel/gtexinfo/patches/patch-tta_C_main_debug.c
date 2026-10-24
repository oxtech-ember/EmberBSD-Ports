$NetBSD$

Print size_t and pointer-sized values with matching conversions.

--- tta/C/main/debug.c.orig
+++ tta/C/main/debug.c
@@ -111,7 +111,7 @@
       if (e->e.c->cmd)
         text_printf (&text, "@%s", debug_element_command_name (e));
       if (e->e.c->contents.number)
-        text_printf (&text, "[C%d]", e->e.c->contents.number);
+        text_printf (&text, "[C%zu]", e->e.c->contents.number);
       if (print_parent && e->e.c->parent)
         {
           text_append (&text, " <- ");
@@ -182,7 +182,7 @@
         case extra_index_entry:
            {
              const INDEX_ENTRY_LOCATION *entry_loc = k->k.index_entry;
-             text_printf (&text, "index_entry: %s, %d",
+             text_printf (&text, "index_entry: %s, %zu",
                           entry_loc->index_name, entry_loc->number);
              break;
            }
