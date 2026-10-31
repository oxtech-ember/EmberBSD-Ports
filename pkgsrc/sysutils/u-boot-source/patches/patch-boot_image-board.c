$NetBSD$

--- a/boot/image-board.c
+++ b/boot/image-board.c
@@ -550,7 +550,7 @@
 		 * turning the "load high" feature off. This is intentional.
 		 */
 		initrd_high = hextoul(s, NULL);
-		if (initrd_high == ~0)
+		if (initrd_high == ~0UL)
 			initrd_copy_to_ram = 0;
 	} else {
 		initrd_high = env_get_bootm_mapsize() + env_get_bootm_low();
