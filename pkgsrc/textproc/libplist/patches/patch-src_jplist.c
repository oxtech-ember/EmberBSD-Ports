$NetBSD$

Return the documented allocation error instead of dereferencing NULL.

--- src/jplist.c.orig
+++ src/jplist.c
@@ -126,6 +126,7 @@
 
     case PLIST_INT:
         val = (char*)malloc(64);
+        if (!val) return PLIST_ERR_NO_MEM;
         if (node_data->length == 16) {
             val_len = snprintf(val, 64, "%" PRIu64, node_data->intval);
         } else {
@@ -137,6 +138,7 @@
 
     case PLIST_REAL:
         val = (char*)malloc(64);
+        if (!val) return PLIST_ERR_NO_MEM;
         val_len = dtostr(val, 64, node_data->realval);
         str_buf_append(*outbuf, val, val_len);
         free(val);
@@ -285,6 +287,7 @@
     case PLIST_UID:
         if (coerce) {
             val = (char*)malloc(64);
+            if (!val) return PLIST_ERR_NO_MEM;
             if (node_data->length == 16) {
                 val_len = snprintf(val, 64, "%" PRIu64, node_data->intval);
             } else {
