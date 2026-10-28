$NetBSD$

Preserve NetBSD and EmberBSD byacc integration changes from the OS source.
Origin: NetBSD and EmberBSD (AI-assisted); not submitted upstream.

--- reader.c.orig
+++ reader.c
@@ -1194,7 +1194,7 @@
     buffer[type2] = '\0';
     (void)trim_blanks(p->type2);
 
-    if (!IS_ALNUM(buffer[name]))
+    if (!IS_ALNUM(UCH(buffer[name])))
     {
 	int n;
 	for (n = name - 1; n >= 0; --n)
@@ -3700,8 +3700,8 @@
     name_pool = TMALLOC(char, name_pool_size);
     NO_SPACE(name_pool);
 
-    strcpy(name_pool, "$accept");
-    strcpy(name_pool + 8, "$end");
+    memcpy(name_pool, "$accept", sizeof("$accept"));
+    memcpy(name_pool + 8, "$end", sizeof("$end"));
     t = name_pool + 13;
     for (bp = first_symbol; bp; bp = bp->next)
     {
