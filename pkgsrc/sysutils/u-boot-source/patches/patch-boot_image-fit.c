$NetBSD$

--- a/boot/image-fit.c
+++ b/boot/image-fit.c
@@ -1351,7 +1351,7 @@
 }
 
 static int fit_image_check_hash(const void *fit, int noffset, const void *data,
-				size_t size, char **err_msgp)
+				size_t size, char **err_msgp, bool quiet)
 {
 	ALLOC_CACHE_ALIGN_BUFFER(uint8_t, value, FIT_MAX_HASH_LEN);
 	int value_len;
@@ -1366,12 +1366,14 @@
 		*err_msgp = "Can't get hash algo property";
 		return -1;
 	}
-	printf("%s", algo);
+	if (!quiet)
+		printf("%s", algo);
 
-	if (!tools_build()) {
+	if (!tools_build() && !CONFIG_IS_ENABLED(FIT_HASH_VERIFY)) {
 		fit_image_hash_get_ignore(fit, noffset, &ignore);
 		if (ignore) {
-			printf("-skipped ");
+			if (!quiet)
+				printf("-skipped ");
 			return 0;
 		}
 	}
@@ -1398,19 +1400,20 @@
 	return 0;
 }
 
-int fit_image_verify_with_data(const void *fit, int image_noffset,
+int fit_image_verify_with_data_quiet(const void *fit, int image_noffset,
 			       const void *key_blob, const void *data,
-			       size_t size)
+			       size_t size, bool quiet, bool *sig_failed)
 {
 	int		noffset = 0;
 	char		*err_msg = "";
 	int verify_all = 1;
+	int hash_count = 0;
 	int ret;
 
 	/* Verify all required signatures */
 	if (FIT_IMAGE_ENABLE_VERIFY &&
-	    fit_image_verify_required_sigs(fit, image_noffset, data, size,
-					   key_blob, &verify_all)) {
+	    fit_image_verify_required_sigs_quiet(fit, image_noffset, data, size,
+					   key_blob, &verify_all, quiet, sig_failed)) {
 		err_msg = "Unable to verify required signature";
 		goto error;
 	}
@@ -1426,15 +1429,17 @@
 		 */
 		if (!strncmp(name, FIT_HASH_NODENAME,
 			     strlen(FIT_HASH_NODENAME))) {
+			hash_count++;
 			if (fit_image_check_hash(fit, noffset, data, size,
-						 &err_msg))
+						 &err_msg, quiet))
 				goto error;
-			puts("+ ");
+			if (!quiet)
+				puts("+ ");
 		} else if (FIT_IMAGE_ENABLE_VERIFY && verify_all &&
 				!strncmp(name, FIT_SIG_NODENAME,
 					strlen(FIT_SIG_NODENAME))) {
-			ret = fit_image_check_sig(fit, noffset, data, size,
-						  gd_fdt_blob(), -1, &err_msg);
+			ret = fit_image_check_sig_quiet(fit, noffset, data, size,
+						  gd_fdt_blob(), -1, &err_msg, quiet);
 
 			/*
 			 * Show an indication on failure, but do not return
@@ -1442,13 +1447,23 @@
 			 * an image validation failure. See the call to
 			 * fit_image_verify_required_sigs() above.
 			 */
-			if (ret)
-				puts("- ");
-			else
-				puts("+ ");
+			if (quiet && ret && sig_failed)
+				*sig_failed = true;
+			if (!quiet) {
+				if (ret)
+					puts("- ");
+				else
+					puts("+ ");
+			}
 		}
 	}
 
+	if (CONFIG_IS_ENABLED(FIT_HASH_VERIFY) && !hash_count) {
+		printf("Missing hash for FIT image '%s'\n",
+		       fit_get_name(fit, image_noffset, NULL));
+		return 0;
+	}
+
 	if (noffset == -FDT_ERR_TRUNCATED || noffset == -FDT_ERR_BADSTRUCTURE) {
 		err_msg = "Corrupted or truncated tree";
 		goto error;
@@ -1463,6 +1478,13 @@
 	return 0;
 }
 
+int fit_image_verify_with_data(const void *fit, int image_noffset,
+		const void *key_blob, const void *data, size_t size)
+{
+	return fit_image_verify_with_data_quiet(fit, image_noffset, key_blob,
+					        data, size, false, NULL);
+}
+
 /**
  * fit_image_verify - verify data integrity
  * @fit: pointer to the FIT format image header
@@ -2261,6 +2283,10 @@
 
 	os_ok = image_type == IH_TYPE_FLATDT ||
 		image_type == IH_TYPE_FPGA ||
+		(IS_ENABLED(CONFIG_RISCV) && image_type == IH_TYPE_KERNEL &&
+		 (fit_image_check_type(fit, noffset, IH_TYPE_KERNEL) ||
+		  fit_image_check_type(fit, noffset, IH_TYPE_KERNEL_NOLOAD)) &&
+		 fit_image_check_os(fit, noffset, IH_OS_NETBSD)) ||
 		fit_image_check_os(fit, noffset, IH_OS_LINUX) ||
 		fit_image_check_os(fit, noffset, IH_OS_U_BOOT) ||
 		fit_image_check_os(fit, noffset, IH_OS_TEE) ||
