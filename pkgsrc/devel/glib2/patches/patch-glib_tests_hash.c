$NetBSD: patch-glib_tests_hash.c,v 1.3 2020/03/04 15:11:48 wiz Exp $

Revert GHashTable improvements
https://gitlab.gnome.org/GNOME/glib/merge_requests/208

to fix PR pkg/54310

--- glib/tests/hash.c.orig
+++ glib/tests/hash.c
@@ -1477,9 +1477,6 @@
   gint             nnodes;
   gint             noccupied;  /* nnodes + tombstones */
 
-  guint            have_big_keys : 1;
-  guint            have_big_values : 1;
-
   gpointer        *keys;
   guint           *hashes;
   gpointer        *values;
@@ -1514,23 +1511,6 @@
     }
 }
 
-#define BIG_ENTRY_SIZE (SIZEOF_VOID_P)
-#define SMALL_ENTRY_SIZE (SIZEOF_INT)
-
-#if SMALL_ENTRY_SIZE < BIG_ENTRY_SIZE
-# define USE_SMALL_ARRAYS
-#endif
-
-static gpointer
-fetch_key_or_value (gpointer a, guint index, gboolean is_big)
-{
-#ifdef USE_SMALL_ARRAYS
-  return is_big ? *(((gpointer *) a) + index) : GUINT_TO_POINTER (*(((guint *) a) + index));
-#else
-  return *(((gpointer *) a) + index);
-#endif
-}
-
 static void
 check_data (GHashTable *h)
 {
@@ -1538,9 +1518,14 @@
 
   for (i = 0; i < h->size; i++)
     {
-      if (h->hashes[i] >= 2)
+      if (h->hashes[i] < 2)
+        {
+          g_assert (h->keys[i] == NULL);
+          g_assert (h->values[i] == NULL);
+        }
+      else
         {
-          g_assert_cmpint (h->hashes[i], ==, h->hash_func (fetch_key_or_value (h->keys, i, h->have_big_keys)));
+          g_assert_cmpint (h->hashes[i], ==, h->hash_func (h->keys[i]));
         }
     }
 }
