$NetBSD$

Return the documented allocation error instead of dereferencing NULL.

--- src/oplist.c.orig
+++ src/oplist.c
@@ -140,6 +140,7 @@
     {
     case PLIST_INT:
         val = (char*)malloc(64);
+        if (!val) return PLIST_ERR_NO_MEM;
         if (node_data->length == 16) {
             val_len = snprintf(val, 64, "%" PRIu64, node_data->intval);
         } else {
@@ -151,6 +152,7 @@
 
     case PLIST_REAL:
         val = (char*)malloc(64);
+        if (!val) return PLIST_ERR_NO_MEM;
         val_len = dtostr(val, 64, node_data->realval);
         str_buf_append(*outbuf, val, val_len);
         free(val);
@@ -330,6 +332,7 @@
     case PLIST_UID:
         if (coerce) {
             val = (char*)malloc(64);
+            if (!val) return PLIST_ERR_NO_MEM;
             if (node_data->length == 16) {
                 val_len = snprintf(val, 64, "%" PRIu64, node_data->intval);
             } else {
@@ -850,6 +853,11 @@
             size_t slen = ctx->pos - p;
             ctx->pos++; // skip the closing quote
             char* strbuf = (char*)malloc(slen+1);
+            if (!strbuf) {
+                plist_free_data(data);
+                ctx->err = PLIST_ERR_NO_MEM;
+                goto err_out;
+            }
             if (num_escapes > 0) {
                 size_t i = 0;
                 size_t o = 0;
