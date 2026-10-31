$NetBSD$

--- a/common/spl/spl_fit.c
+++ b/common/spl/spl_fit.c
@@ -389,7 +389,7 @@
 		src = (void *)data;	/* cast away const */
 	}
 
-	if (CONFIG_IS_ENABLED(FIT_SIGNATURE)) {
+	if (CONFIG_IS_ENABLED(FIT_SIGNATURE) || CONFIG_IS_ENABLED(FIT_HASH_VERIFY)) {
 		printf("## Checking hash(es) for Image %s ... ",
 		       fit_get_name(fit, node, NULL));
 		if (!fit_image_verify_with_data(fit, node, gd_fdt_blob(), src,
@@ -770,7 +770,7 @@
 			       struct spl_load_info *info, ulong offset,
 			       const void *fit_header)
 {
-	unsigned long aligned_size, count, size;
+	unsigned long aligned_size, count, fit_size, size;
 	void *buf;
 	int ret;
 
@@ -779,8 +779,15 @@
 	 * start. This is the base for the data-offset properties in each
 	 * image.
 	 */
-	size = ALIGN(fdt_totalsize(fit_header), 4);
+	fit_size = fdt_totalsize(fit_header);
+	if (fit_size < sizeof(struct fdt_header))
+		return -EINVAL;
+	if (fit_size > ULONG_MAX - 3)
+		return -EOVERFLOW;
+	size = ALIGN(fit_size, 4);
 	size = board_spl_fit_size_align(size);
+	if (size < fit_size || size > ULONG_MAX - 3)
+		return -EOVERFLOW;
 	ctx->ext_data_offset = ALIGN(size, 4);
 
 	/*
@@ -806,7 +813,7 @@
 	}
 
 	count = info->read(info, offset, aligned_size, buf);
-	if (!count) {
+	if (count < fit_size || count > aligned_size) {
 		/*
 		 * FIT could not be read. This means we should free the
 		 * memory allocated by board_spl_fit_buffer_addr().
@@ -837,6 +844,11 @@
 	}
 
 	ctx->fit = buf;
+	if (CONFIG_IS_ENABLED(FIT_FULL_CHECK)) {
+		ret = fit_check_format(ctx->fit, count);
+		if (ret)
+			return ret;
+	}
 	debug("fit read offset %lx, size=%lu, dst=%p, count=%lu\n",
 	      offset, aligned_size, buf, count);
 
@@ -981,8 +993,11 @@
 			debug("Loadable is %s\n", genimg_get_os_name(os_type));
 
 		if (os_takes_devicetree(os_type)) {
-			spl_fit_append_fdt(&image_info, info, offset, &ctx);
-			spl_image->fdt_addr = image_info.fdt_addr;
+			ret = spl_fit_append_fdt(&image_info, info, offset, &ctx);
+			if (ret < 0 && os_type != IH_OS_U_BOOT)
+				return ret;
+			if (ret >= 0)
+				spl_image->fdt_addr = image_info.fdt_addr;
 		}
 
 		/*
