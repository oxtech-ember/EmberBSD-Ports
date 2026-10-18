$NetBSD$

Initialize the write buffers before a deferred seek writes zero bytes.
gzputc() can enter gz_zero() before the first compression call. Without
this initialization, gz_zero() reads an uninitialized input pointer and
can compress uninitialized bytes instead of the requested zero fill.

Origin: EmberBSD (AI-assisted). Not submitted upstream.

--- gzwrite.c.orig
+++ gzwrite.c
@@ -156,6 +156,10 @@
     unsigned n;
     z_streamp strm = &(state->strm);
 
+    /* a seek can precede the first write */
+    if (state->size == 0 && gz_init(state) == -1)
+        return -1;
+
     /* consume whatever's left in the input buffer */
     if (strm->avail_in && gz_comp(state, Z_NO_FLUSH) == -1)
         return -1;
