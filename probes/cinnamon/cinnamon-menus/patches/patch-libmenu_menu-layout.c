$NetBSD$

Origin: EmberBSD (AI-assisted). Use the current GLib transfer API so the
menu name buffer remains owned by the tree and the returned pointer is used.

--- libmenu/menu-layout.c.orig
+++ libmenu/menu-layout.c
@@ -2307,10 +2307,9 @@ menu_layout_load (const char  *filename,
   if (g_str_has_suffix (str->str, ".menu"))
     g_string_truncate (str, str->len - strlen (".menu"));
 
-  root->name = str->str;
+  root->name = g_string_free_and_steal (str);
   menu_verbose ("Set menu name \"%s\"\n", root->name);
 
-  g_string_free (str, FALSE);
   g_free (s);
 
   context = g_markup_parse_context_new (&menu_funcs, 0, &parser, NULL);
