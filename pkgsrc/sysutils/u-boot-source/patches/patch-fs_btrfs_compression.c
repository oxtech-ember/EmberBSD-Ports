$NetBSD$

--- a/fs/btrfs/compression.c
+++ b/fs/btrfs/compression.c
@@ -92,6 +92,8 @@
 	u32 res;
 
 	memset(&stream, 0, sizeof(stream));
+	stream.zalloc = gzalloc;
+	stream.zfree = gzfree;
 
 	cbuf = (u8 *) _cbuf;
 
