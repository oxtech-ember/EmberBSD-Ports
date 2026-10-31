$NetBSD$

--- a/common/spl/spl_ymodem.c
+++ b/common/spl/spl_ymodem.c
@@ -9,6 +9,7 @@
  * Matt Porter <mporter@ti.com>
  */
 #include <gzip.h>
+#include <errno.h>
 #include <image.h>
 #include <log.h>
 #include <spl.h>
@@ -20,11 +21,13 @@
 /*
  * Information required to load image using ymodem.
  *
- * @image_read: Now of bytes read from the image.
- * @buf: pointer to the previous read block.
+ * @image_read: Number of bytes read from the image.
+ * @buf_size: Number of valid bytes in the previous read block.
+ * @buf: Pointer to the previous read block.
  */
 struct ymodem_fit_info {
-	int image_read;
+	ulong image_read;
+	int buf_size;
 	char *buf;
 };
 
@@ -38,31 +41,41 @@
 			     ulong size, void *addr)
 {
 	int res, err, buf_offset;
+	ulong buffered;
 	struct ymodem_fit_info *info = load->priv;
 	char *buf = info->buf;
+	char *dest = addr;
 	ulong copy_size = size;
+
+	if (size > ~0UL - offset)
+		return 0;
 
 	while (info->image_read < offset) {
 		res = xyzModem_stream_read(buf, BUF_SIZE, &err);
 		if (res <= 0)
-			break;
-
+			return 0;
+
+		if ((ulong)res > ~0UL - info->image_read)
+			return 0;
 		info->image_read += res;
+		info->buf_size = res;
 	}
 
 	if (info->image_read > offset) {
-		res = info->image_read - offset;
-		if (info->image_read % BUF_SIZE)
-			buf_offset = (info->image_read % BUF_SIZE);
-		else
-			buf_offset = BUF_SIZE;
+		buffered = info->image_read - offset;
+		buf_offset = info->buf_size;
+		/* A sequential stream cannot revisit bytes no longer buffered. */
+		if (buffered > (ulong)buf_offset)
+			return 0;
+		res = buffered;
 
 		if (res > copy_size) {
-			memcpy(addr, &buf[buf_offset - res], copy_size);
+			memcpy(dest, &buf[buf_offset - res], copy_size);
+			copy_size = 0;
 			goto done;
 		}
-		memcpy(addr, &buf[buf_offset - res], res);
-		addr = addr + res;
+		memcpy(dest, &buf[buf_offset - res], res);
+		dest += res;
 		copy_size -= res;
 	}
 
@@ -71,18 +84,22 @@
 		if (res <= 0)
 			break;
 
+		if ((ulong)res > ~0UL - info->image_read)
+			return 0;
 		info->image_read += res;
+		info->buf_size = res;
 		if (res > copy_size) {
-			memcpy(addr, buf, copy_size);
+			memcpy(dest, buf, copy_size);
+			copy_size = 0;
 			goto done;
 		}
-		memcpy(addr, buf, res);
-		addr += res;
+		memcpy(dest, buf, res);
+		dest += res;
 		copy_size -= res;
 	}
 
 done:
-	return size;
+	return copy_size ? 0 : size;
 }
 
 int spl_ymodem_load_image(struct spl_image_info *spl_image,
@@ -96,6 +113,7 @@
 	char buf[BUF_SIZE];
 	struct legacy_img_hdr *ih = NULL;
 	ulong addr = 0;
+	bool fit;
 
 	info.mode = xyzModem_ymodem;
 	ret = xyzModem_stream_open(&info, &err);
@@ -105,11 +123,13 @@
 	}
 
 	res = xyzModem_stream_read(buf, BUF_SIZE, &err);
-	if (res <= 0)
+	if (res < (int)sizeof(*ih)) {
+		ret = -EIO;
 		goto end_stream;
-
-	if (IS_ENABLED(CONFIG_SPL_LOAD_FIT_FULL) &&
-	    image_get_magic((struct legacy_img_hdr *)buf) == FDT_MAGIC) {
+	}
+
+	fit = image_get_magic((struct legacy_img_hdr *)buf) == FDT_MAGIC;
+	if (IS_ENABLED(CONFIG_SPL_LOAD_FIT_FULL) && fit) {
 		addr = CONFIG_SYS_LOAD_ADDR;
 		ih = (struct legacy_img_hdr *)addr;
 
@@ -125,16 +145,16 @@
 
 		ret = spl_parse_image_header(spl_image, bootdev, ih);
 		if (ret)
-			return ret;
-	} else if (IS_ENABLED(CONFIG_SPL_LOAD_FIT) &&
-	    image_get_magic((struct legacy_img_hdr *)buf) == FDT_MAGIC) {
+			goto end_stream;
+	} else if (IS_ENABLED(CONFIG_SPL_LOAD_FIT) && fit) {
 		struct spl_load_info load;
 		struct ymodem_fit_info info;
 
 		debug("Found FIT\n");
 		spl_load_init(&load, ymodem_read_fit, (void *)&info, 1);
 		info.buf = buf;
-		info.image_read = BUF_SIZE;
+		info.image_read = res;
+		info.buf_size = res;
 		ret = spl_load_simple_fit(spl_image, &load, 0, (void *)buf);
 		size = info.image_read;
 
@@ -152,7 +172,9 @@
 #endif
 			addr = spl_image->load_addr;
 		memcpy((void *)addr, buf, res);
+#ifdef CONFIG_SPL_GZIP
 		ih = (struct legacy_img_hdr *)addr;
+#endif
 		size += res;
 		addr += res;
 
@@ -170,9 +192,7 @@
 	printf("Loaded %lu bytes\n", size);
 
 #ifdef CONFIG_SPL_GZIP
-	if (!(IS_ENABLED(CONFIG_SPL_LOAD_FIT) &&
-	      image_get_magic((struct legacy_img_hdr *)buf) == FDT_MAGIC) &&
-	    (ih->ih_comp == IH_COMP_GZIP)) {
+	if (!ret && !fit && ih->ih_comp == IH_COMP_GZIP) {
 		if (gunzip((void *)(spl_image->load_addr + sizeof(*ih)),
 			   CONFIG_SYS_BOOTM_LEN,
 			   (void *)(CONFIG_SYS_LOAD_ADDR + sizeof(*ih)),
