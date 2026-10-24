$NetBSD$

Copy the tube name with an explicit length.
The strncpy() call stops the build with -Werror=stringop-truncation.

--- tube.c.orig
+++ tube.c
@@ -12,11 +12,13 @@
     if (!t)
         return NULL;
 
-    strncpy(t->name, name, MAX_TUBE_NAME_LEN);
-    if (t->name[MAX_TUBE_NAME_LEN - 1] != '\0') {
-        t->name[MAX_TUBE_NAME_LEN - 1] = '\0';
+    size_t len = strnlen(name, MAX_TUBE_NAME_LEN);
+    if (len == MAX_TUBE_NAME_LEN) {
+        len = MAX_TUBE_NAME_LEN - 1;
         twarnx("truncating tube name");
     }
+    memcpy(t->name, name, len);
+    t->name[len] = '\0';
 
     t->ready.less = job_pri_less;
     t->delay.less = job_delay_less;
