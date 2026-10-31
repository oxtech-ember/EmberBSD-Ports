$NetBSD$

--- a/fs/cramfs/uncompress.c
+++ b/fs/cramfs/uncompress.c
@@ -41,7 +41,13 @@
 	stream.next_out = dst;
 	stream.avail_out = 4096 * 2;
 
+#if defined(CONFIG_HW_WATCHDOG) || defined(CONFIG_WATCHDOG)
+	schedule();
+#endif
 	err = inflate (&stream, Z_FINISH);
+#if defined(CONFIG_HW_WATCHDOG) || defined(CONFIG_WATCHDOG)
+	schedule();
+#endif
 
 	if (err != Z_STREAM_END)
 		goto err;
@@ -62,11 +68,6 @@
 	stream.next_in = 0;
 	stream.avail_in = 0;
 
-#if defined(CONFIG_HW_WATCHDOG) || defined(CONFIG_WATCHDOG)
-	stream.outcb = (cb_func)schedule;
-#else
-	stream.outcb = Z_NULL;
-#endif /* CONFIG_HW_WATCHDOG */
 
 	err = inflateInit (&stream);
 	if (err != Z_OK) {
