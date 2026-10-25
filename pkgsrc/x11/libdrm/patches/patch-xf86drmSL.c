Origin: AI-assisted; upstream libdrm 2.4.134 xf86drmSL.c. Return cleanly on skip-list allocation failures.

--- xf86drmSL.c.orig
+++ xf86drmSL.c
@@ -93,6 +93,7 @@
     SL_RANDOM_DECL;
 
     SL_RANDOM_INIT(SL_RANDOM_SEED);
+    if (!state) return -1;
     
     while ((SL_RANDOM & 0x01) && level < SL_MAX_LEVEL) ++level;
     return level;
@@ -108,6 +109,10 @@
     list->magic    = SL_LIST_MAGIC;
     list->level    = 0;
     list->head     = SLCreateEntry(SL_MAX_LEVEL, 0, NULL);
+    if (!list->head) {
+	drmFree(list);
+	return NULL;
+    }
     list->count    = 0;
 
     for (i = 0; i <= SL_MAX_LEVEL; i++) list->head->forward[i] = NULL;
@@ -159,6 +164,7 @@
     SLEntryPtr    update[SL_MAX_LEVEL + 1];
     int           level;
     int           i;
+    int           level_increased = 0;
 
     if (list->magic != SL_LIST_MAGIC) return -1; /* Bad magic */
 
@@ -168,12 +174,18 @@
 
 
     level = SLRandomLevel();
+    if (level < 0) return -1;
     if (level > list->level) {
 	level = ++list->level;
 	update[level] = list->head;
+	level_increased = 1;
     }
 
     entry = SLCreateEntry(level, key, value);
+    if (!entry) {
+	if (level_increased) --list->level;
+	return -1;
+    }
 
 				/* Fix up forward pointers */
     for (i = 0; i <= level; i++) {
