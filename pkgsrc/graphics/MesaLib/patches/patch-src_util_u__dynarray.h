$NetBSD$

Avoid an overlapping memcpy when deleting the last array element. NetBSD's
fortified memcpy rejects self-copy, which otherwise aborts NIR compilation.
Origin: EmberBSD contributors (AI-assisted).

--- src/util/u_dynarray.h
+++ src/util/u_dynarray.h
@@ -260,8 +260,10 @@
       for (i = 0; i < num_elements; i++) {                              \
          type __v = *util_dynarray_element((buf), type, (i));           \
          if (v == __v) {                                                \
-            memcpy(util_dynarray_element((buf), type, (i)),             \
-                   util_dynarray_pop_ptr((buf), type), sizeof(type));   \
+            type *__dst = util_dynarray_element((buf), type, i);         \
+            type *__last = util_dynarray_pop_ptr((buf), type);          \
+            if (__dst != __last)                                        \
+               memcpy(__dst, __last, sizeof(type));                     \
             break;                                                      \
          }                                                              \
       }                                                                 \
