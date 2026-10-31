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
@@ -20,11 +21,14 @@
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
+	int stream_err;
 	char *buf;
 };
 
@@ -37,65 +41,92 @@
 static ulong ymodem_read_fit(struct spl_load_info *load, ulong offset,
 			     ulong size, void *addr)
 {
-	int res, err, buf_offset;
+	int res, err = 0, buf_offset;
+	ulong buffered;
 	struct ymodem_fit_info *info = load->priv;
 	char *buf = info->buf;
+	char *dest = addr;
 	ulong copy_size = size;
 
+	if (size > ~0UL - offset)
+		return 0;
+
 	while (info->image_read < offset) {
 		res = xyzModem_stream_read(buf, BUF_SIZE, &err);
+		if (err < 0 && err != xyzModem_eof) {
+			info->stream_err = err;
+			return 0;
+		}
 		if (res <= 0)
-			break;
+			return 0;
 
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
 
 	while (info->image_read < offset + size) {
 		res = xyzModem_stream_read(buf, BUF_SIZE, &err);
+		if (err < 0 && err != xyzModem_eof) {
+			info->stream_err = err;
+			return 0;
+		}
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
 			  struct spl_boot_device *bootdev)
 {
 	ulong size = 0;
-	int err;
+	int err = 0;
 	int res;
 	int ret;
 	connection_info_t info;
 	char buf[BUF_SIZE];
 	struct legacy_img_hdr *ih = NULL;
 	ulong addr = 0;
+	bool fit = false;
+	bool fit_verified = false;
+	bool sig_failed = false;
+	bool fit_deprecated = false;
+	bool fpga_loaded = false;
 
 	info.mode = xyzModem_ymodem;
 	ret = xyzModem_stream_open(&info, &err);
@@ -105,11 +136,14 @@
 	}
 
 	res = xyzModem_stream_read(buf, BUF_SIZE, &err);
-	if (res <= 0)
+	if (res < (int)sizeof(*ih) ||
+	    (err < 0 && err != xyzModem_eof)) {
+		ret = -EIO;
 		goto end_stream;
+	}
 
-	if (IS_ENABLED(CONFIG_SPL_LOAD_FIT_FULL) &&
-	    image_get_magic((struct legacy_img_hdr *)buf) == FDT_MAGIC) {
+	fit = image_get_magic((struct legacy_img_hdr *)buf) == FDT_MAGIC;
+	if (IS_ENABLED(CONFIG_SPL_LOAD_FIT_FULL) && fit) {
 		addr = CONFIG_SYS_LOAD_ADDR;
 		ih = (struct legacy_img_hdr *)addr;
 
@@ -118,6 +152,10 @@
 		addr += res;
 
 		while ((res = xyzModem_stream_read(buf, BUF_SIZE, &err)) > 0) {
+			if (err < 0 && err != xyzModem_eof) {
+				ret = -EIO;
+				goto end_stream;
+			}
 			memcpy((void *)addr, buf, res);
 			size += res;
 			addr += res;
@@ -125,21 +163,34 @@
 
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
+		load.fit_quiet = true;
 		info.buf = buf;
-		info.image_read = BUF_SIZE;
+		info.image_read = res;
+		info.buf_size = res;
+		info.stream_err = 0;
 		ret = spl_load_simple_fit(spl_image, &load, 0, (void *)buf);
+		sig_failed = load.fit_signature_failed;
+		fit_deprecated = load.fit_deprecated;
+		fpga_loaded = load.fit_fpga_loaded;
+		if (!ret && info.stream_err < 0)
+			ret = -EIO;
+		fit_verified = !ret;
 		size = info.image_read;
 
-		while ((res = xyzModem_stream_read(buf, BUF_SIZE, &err)) > 0)
+		while ((res = xyzModem_stream_read(buf, BUF_SIZE, &err)) > 0) {
+			if (err < 0 && err != xyzModem_eof) {
+				ret = -EIO;
+				goto end_stream;
+			}
 			size += res;
+		}
 	} else {
 		ih = (struct legacy_img_hdr *)buf;
 		ret = spl_parse_image_header(spl_image, bootdev, ih);
@@ -152,11 +203,17 @@
 #endif
 			addr = spl_image->load_addr;
 		memcpy((void *)addr, buf, res);
+#ifdef CONFIG_SPL_GZIP
 		ih = (struct legacy_img_hdr *)addr;
+#endif
 		size += res;
 		addr += res;
 
 		while ((res = xyzModem_stream_read(buf, BUF_SIZE, &err)) > 0) {
+			if (err < 0 && err != xyzModem_eof) {
+				ret = -EIO;
+				goto end_stream;
+			}
 			memcpy((void *)addr, buf, res);
 			size += res;
 			addr += res;
@@ -164,15 +221,23 @@
 	}
 
 end_stream:
+	if (!ret && err < 0 && err != xyzModem_eof)
+		ret = -EIO;
 	xyzModem_stream_close(&err);
 	xyzModem_stream_terminate(false, &getcymodem);
 
 	printf("Loaded %lu bytes\n", size);
+	if (fit_deprecated)
+		puts("DEPRECATED: FPGA FIT metadata; see https://fitspec.osfw.foundation/\n");
+	if (fpga_loaded)
+		puts("FPGA image loaded from FIT\n");
+	if (sig_failed)
+		puts("One or more FIT signature attempts failed\n");
+	if (!ret && fit_verified && CONFIG_IS_ENABLED(FIT_HASH_VERIFY))
+		puts("Loaded FIT images: hashes verified\n");
 
 #ifdef CONFIG_SPL_GZIP
-	if (!(IS_ENABLED(CONFIG_SPL_LOAD_FIT) &&
-	      image_get_magic((struct legacy_img_hdr *)buf) == FDT_MAGIC) &&
-	    (ih->ih_comp == IH_COMP_GZIP)) {
+	if (!ret && !fit && ih->ih_comp == IH_COMP_GZIP) {
 		if (gunzip((void *)(spl_image->load_addr + sizeof(*ih)),
 			   CONFIG_SYS_BOOTM_LEN,
 			   (void *)(CONFIG_SYS_LOAD_ADDR + sizeof(*ih)),
