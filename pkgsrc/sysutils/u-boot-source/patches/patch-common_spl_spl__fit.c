$NetBSD$

--- a/common/spl/spl_fit.c
+++ b/common/spl/spl_fit.c
@@ -389,13 +389,16 @@
 		src = (void *)data;	/* cast away const */
 	}
 
-	if (CONFIG_IS_ENABLED(FIT_SIGNATURE)) {
-		printf("## Checking hash(es) for Image %s ... ",
-		       fit_get_name(fit, node, NULL));
-		if (!fit_image_verify_with_data(fit, node, gd_fdt_blob(), src,
-						length))
+	if (CONFIG_IS_ENABLED(FIT_SIGNATURE) || CONFIG_IS_ENABLED(FIT_HASH_VERIFY)) {
+		if (!info->fit_quiet)
+			printf("## Checking hash(es) for Image %s ... ",
+			       fit_get_name(fit, node, NULL));
+		if (!fit_image_verify_with_data_quiet(fit, node, gd_fdt_blob(), src,
+						length, info->fit_quiet,
+						&info->fit_signature_failed))
 			return -EPERM;
-		puts("OK\n");
+		if (!info->fit_quiet)
+			puts("OK\n");
 	}
 
 	if (CONFIG_IS_ENABLED(FIT_IMAGE_POST_PROCESS))
@@ -700,14 +703,19 @@
 	return (void *)fit;
 }
 
-static void warn_deprecated(const char *msg)
+static void warn_deprecated(const char *msg, struct spl_load_info *info)
 {
+	if (info->fit_quiet) {
+		info->fit_deprecated = true;
+		return;
+	}
 	printf("DEPRECATED: %s\n", msg);
 	printf("\tSee https://fitspec.osfw.foundation/\n");
 }
 
 static int spl_fit_upload_fpga(struct spl_fit_info *ctx, int node,
-			       struct spl_image_info *fpga_image)
+			       struct spl_image_info *fpga_image,
+			       struct spl_load_info *info)
 {
 	const char *compatible;
 	int ret;
@@ -719,7 +727,7 @@
 
 	compatible = fdt_getprop(ctx->fit, node, "compatible", NULL);
 	if (!compatible) {
-		warn_deprecated("'fpga' image without 'compatible' property");
+		warn_deprecated("'fpga' image without 'compatible' property", info);
 	} else {
 		if (CONFIG_IS_ENABLED(FPGA_LOAD_SECURE))
 			flags = fpga_compatible2flag(devnum, compatible);
@@ -735,7 +743,10 @@
 		return ret;
 	}
 
-	puts("FPGA image loaded from FIT\n");
+	if (info->fit_quiet)
+		info->fit_fpga_loaded = true;
+	else
+		puts("FPGA image loaded from FIT\n");
 
 	return 0;
 }
@@ -753,7 +764,7 @@
 	if (node < 0)
 		return node;
 
-	warn_deprecated("'fpga' property in config node. Use 'loadables'");
+	warn_deprecated("'fpga' property in config node. Use 'loadables'", info);
 
 	/* Load the image and set up the fpga_image structure */
 	ret = load_simple_fit(info, offset, ctx, node, &fpga_image,
@@ -763,14 +774,14 @@
 		return ret;
 	}
 
-	return spl_fit_upload_fpga(ctx, node, &fpga_image);
+	return spl_fit_upload_fpga(ctx, node, &fpga_image, info);
 }
 
 static int spl_simple_fit_read(struct spl_fit_info *ctx,
 			       struct spl_load_info *info, ulong offset,
 			       const void *fit_header)
 {
-	unsigned long aligned_size, count, size;
+	unsigned long aligned_size, count, fit_size, size;
 	void *buf;
 	int ret;
 
@@ -779,8 +790,15 @@
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
@@ -806,7 +824,7 @@
 	}
 
 	count = info->read(info, offset, aligned_size, buf);
-	if (!count) {
+	if (count < fit_size || count > aligned_size) {
 		/*
 		 * FIT could not be read. This means we should free the
 		 * memory allocated by board_spl_fit_buffer_addr().
@@ -837,13 +855,19 @@
 	}
 
 	ctx->fit = buf;
+	if (CONFIG_IS_ENABLED(FIT_FULL_CHECK)) {
+		ret = fit_check_format(ctx->fit, count);
+		if (ret)
+			return ret;
+	}
 	debug("fit read offset %lx, size=%lu, dst=%p, count=%lu\n",
 	      offset, aligned_size, buf, count);
 
 	return 0;
 }
 
-static int spl_simple_fit_parse(struct spl_fit_info *ctx)
+static int spl_simple_fit_parse(struct spl_fit_info *ctx,
+				struct spl_load_info *info)
 {
 	/* Find the correct subnode under "/configurations" */
 	ctx->conf_node = fit_find_config_node(ctx->fit);
@@ -851,11 +875,14 @@
 		return -EINVAL;
 
 	if (CONFIG_IS_ENABLED(FIT_SIGNATURE)) {
-		printf("## Checking hash(es) for config %s ... ",
-		       fit_get_name(ctx->fit, ctx->conf_node, NULL));
-		if (fit_config_verify(ctx->fit, ctx->conf_node))
+		if (!info->fit_quiet)
+			printf("## Checking hash(es) for config %s ... ",
+			       fit_get_name(ctx->fit, ctx->conf_node, NULL));
+		if (fit_config_verify_quiet(ctx->fit, ctx->conf_node, info->fit_quiet,
+					    &info->fit_signature_failed))
 			return -EPERM;
-		puts("OK\n");
+		if (!info->fit_quiet)
+			puts("OK\n");
 	}
 
 	/* find the node holding the images information */
@@ -889,7 +916,7 @@
 
 	ctx.fit = spl_load_simple_fit_fix_load(ctx.fit);
 
-	ret = spl_simple_fit_parse(&ctx);
+	ret = spl_simple_fit_parse(&ctx, info);
 	if (ret < 0)
 		return ret;
 
@@ -975,14 +1002,17 @@
 		}
 
 		if (spl_fit_image_is_fpga(ctx.fit, node))
-			spl_fit_upload_fpga(&ctx, node, &image_info);
+			spl_fit_upload_fpga(&ctx, node, &image_info, info);
 
 		if (!spl_fit_image_get_os(ctx.fit, node, &os_type))
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
