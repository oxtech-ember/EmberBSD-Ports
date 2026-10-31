$NetBSD$

--- a/lib/gzip.c
+++ b/lib/gzip.c
@@ -30,7 +30,7 @@
 	return (p);
 }
 
-static void zfree(void *x, void *addr, unsigned nb)
+static void zfree(void *x, void *addr)
 {
 	free (addr);
 }
@@ -67,7 +67,7 @@
 
 	r = deflateInit2_(&s, Z_BEST_SPEED, Z_DEFLATED,	window,
 			DEF_MEM_LEVEL, Z_DEFAULT_STRATEGY,
-			sizeof(z_stream));
+			ZLIB_VERSION, sizeof(z_stream));
 	if (r != Z_OK) {
 		printf ("Error: deflateInit2_() returned %d\n", r);
 		return -1;
@@ -94,7 +94,7 @@
 				goto bail;
 			}
 			if (!func) {
-				dst += (left_len - s.avail_out);
+				dst = (unsigned char *)dst + (left_len - s.avail_out);
 				*lenp -= (left_len - s.avail_out);
 			} else if (left_len - s.avail_out > 0) {
 				r = func((unsigned long)dst,
