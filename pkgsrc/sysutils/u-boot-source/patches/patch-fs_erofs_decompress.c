$NetBSD$

--- a/fs/erofs/decompress.c
+++ b/fs/erofs/decompress.c
@@ -44,8 +44,8 @@
 	}
 
 	/* allocate inflate state */
-	strm.zalloc = Z_NULL;
-	strm.zfree = Z_NULL;
+	strm.zalloc = gzalloc;
+	strm.zfree = gzfree;
 	strm.opaque = Z_NULL;
 	strm.avail_in = 0;
 	strm.next_in = Z_NULL;
