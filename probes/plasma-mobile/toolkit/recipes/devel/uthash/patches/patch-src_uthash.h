$NetBSD$

Compute the secondary hash-handle offset from a valid source element.
HASH_SELECT permits an empty destination and an empty source.
Do not access a member through the null destination pointer.

--- src/uthash.h.orig
+++ src/uthash.h
@@ -981,8 +981,9 @@
   unsigned _src_bkt, _dst_bkt;                                                   \
   void *_last_elt = NULL, *_elt;                                                 \
   UT_hash_handle *_src_hh, *_dst_hh, *_last_elt_hh=NULL;                         \
-  ptrdiff_t _dst_hho = ((char*)(&(dst)->hh_dst) - (char*)(dst));                 \
+  ptrdiff_t _dst_hho;                                                            \
   if ((src) != NULL) {                                                           \
+    _dst_hho = ((char*)(&(src)->hh_dst) - (char*)(src));                        \
     for (_src_bkt=0; _src_bkt < (src)->hh_src.tbl->num_buckets; _src_bkt++) {    \
       for (_src_hh = (src)->hh_src.tbl->buckets[_src_bkt].hh_head;               \
         _src_hh != NULL;                                                         \
