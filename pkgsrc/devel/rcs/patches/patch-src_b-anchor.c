# Origin: EmberBSD (AI-assisted).
Preserve the configured local Id keyword in the common RCS source.

--- src/b-anchor.c.orig
+++ src/b-anchor.c
@@ -106,7 +106,7 @@
       if (x->size == symlen && MEM_SAME (symlen, p + 1, x->string))
         {
           found->i = i;
-          found->sym = (struct tinysym const *) p;
+          found->name = (char const *) p + 1;
           return true;
         }
       p += 1 + symlen + 1;
@@ -172,9 +172,20 @@
       .size = limit
     };
 
-  return ((KDELIM == string[limit]
-           || VDELIM == string[limit])
-          && pool_lookup (keyword_pool, &x, found));
+  if (KDELIM != string[limit] && VDELIM != string[limit])
+    return false;
+  if (pool_lookup (keyword_pool, &x, found))
+    return true;
+#ifdef LOCALID
+  /* Treat the configured local keyword like Id, preserving its spelling.  */
+  if (x.size == sizeof LOCALID - 1 && MEM_SAME (x.size, LOCALID, x.string))
+    {
+      found->i = Id;
+      found->name = LOCALID;
+      return true;
+    }
+#endif
+  return false;
 }
 
 /* b-anchor.c ends here */
