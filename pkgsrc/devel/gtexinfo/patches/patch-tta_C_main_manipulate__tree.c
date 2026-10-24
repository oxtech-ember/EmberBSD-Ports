$NetBSD$

Print size_t and pointer-sized values with matching conversions.

--- tta/C/main/manipulate_tree.c.orig
+++ tta/C/main/manipulate_tree.c
@@ -1148,7 +1148,7 @@
       else /* none */
         text_printf (result, "<%d>", s_mark->counter);
       if (s_mark->position)
-        text_printf (result, "<p:%d>", s_mark->position);
+        text_printf (result, "<p:%zu>", s_mark->position);
       if (s_mark->line)
         {
           char *sm_line = debug_protect_eol (s_mark->line);
@@ -1398,7 +1398,8 @@
   if (element->flags & EF_numbered)
     {
       int elt_info_nr = type_data[element->type].elt_info_number;
-      xasprintf (&result, "E%" PRIuPTR, element->elt_info[elt_info_nr]);
+      xasprintf (&result, "E%" PRIuPTR,
+                 (uintptr_t) element->elt_info[elt_info_nr]);
     }
   else
     {
@@ -1544,7 +1545,7 @@
         case extra_index_entry:
           {
             const INDEX_ENTRY_LOCATION *entry_loc = k_pair->k.index_entry;
-            xasprintf (&value, "I{%s,%d}",
+            xasprintf (&value, "I{%s,%zu}",
                        entry_loc->index_name, entry_loc->number);
             break;
           }
@@ -1665,7 +1666,8 @@
   if (element->flags & EF_numbered)
     {
       int elt_info_nr = type_data[element->type].elt_info_number;
-      text_printf (result, "%" PRIuPTR " ", element->elt_info[elt_info_nr]);
+      text_printf (result, "%" PRIuPTR " ",
+                   (uintptr_t) element->elt_info[elt_info_nr]);
     }
 
   if (element->type
