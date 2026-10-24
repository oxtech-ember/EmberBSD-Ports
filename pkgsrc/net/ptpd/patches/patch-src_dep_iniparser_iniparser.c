$NetBSD$

Pass ctype functions an unsigned char value: a UTF-8 byte in a
configuration comment is a negative char and crashed the parser.

--- src/dep/iniparser/iniparser.c.orig
+++ src/dep/iniparser/iniparser.c
@@ -50,7 +50,7 @@
     memset(l, 0, ASCIILINESZ+1);
     i=0 ;
     while (s[i] && i<ASCIILINESZ) {
-        l[i] = (char)tolower((int)s[i]);
+        l[i] = (char)tolower((unsigned char)s[i]);
         i++ ;
     }
     l[ASCIILINESZ]=(char)0;
@@ -78,12 +78,12 @@
    
     if (s==NULL) return NULL ;
    
-    while (isspace((int)*s) && *s) s++;
+    while (isspace((unsigned char)*s) && *s) s++;
     memset(l, 0, ASCIILINESZ+1);
     strncpy(l, s, ASCIILINESZ);
     last = l + strlen(l);
     while (last > l) {
-        if (!isspace((int)*(last-1)))
+        if (!isspace((unsigned char)*(last-1)))
             break ;
         last -- ;
     }
