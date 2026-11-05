# $NetBSD$

Preserve desktop-app cmark-gfm hardening changes from upstream fork
3b2bbdc028c1747d1e50d1a32c7f7c61e58c8133,
48a0cf99150a42617762ae67cae65f9a5b88647a and
d7d4a24a9ebfa7581994ea6df0297662bfeaf413.

--- src/buffer.c.orig
+++ src/buffer.c
@@ -32,7 +32,11 @@
 }
 
 static CMARK_INLINE void S_strbuf_grow_by(cmark_strbuf *buf, bufsize_t add) {
-  cmark_strbuf_grow(buf, buf->size + add);
+  // Route sums that would overflow bufsize_t through the oversized-buffer
+  // limit in cmark_strbuf_grow instead of wrapping the grow target negative.
+  cmark_strbuf_grow(buf, (add < 0 || buf->size > INT32_MAX - add)
+                             ? INT32_MAX
+                             : buf->size + add);
 }
 
 void cmark_strbuf_grow(cmark_strbuf *buf, bufsize_t target_size) {
