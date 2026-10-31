$NetBSD$

--- a/boot/image-fit.c
+++ b/boot/image-fit.c
@@ -1368,7 +1368,7 @@
 	}
 	printf("%s", algo);
 
-	if (!tools_build()) {
+	if (!tools_build() && !CONFIG_IS_ENABLED(FIT_HASH_VERIFY)) {
 		fit_image_hash_get_ignore(fit, noffset, &ignore);
 		if (ignore) {
 			printf("-skipped ");
@@ -1405,6 +1405,7 @@
 	int		noffset = 0;
 	char		*err_msg = "";
 	int verify_all = 1;
+	int hash_count = 0;
 	int ret;
 
 	/* Verify all required signatures */
@@ -1426,6 +1427,7 @@
 		 */
 		if (!strncmp(name, FIT_HASH_NODENAME,
 			     strlen(FIT_HASH_NODENAME))) {
+			hash_count++;
 			if (fit_image_check_hash(fit, noffset, data, size,
 						 &err_msg))
 				goto error;
@@ -1447,6 +1449,12 @@
 			else
 				puts("+ ");
 		}
+	}
+
+	if (CONFIG_IS_ENABLED(FIT_HASH_VERIFY) && !hash_count) {
+		printf("Missing hash for FIT image '%s'\n",
+		       fit_get_name(fit, image_noffset, NULL));
+		return 0;
 	}
 
 	if (noffset == -FDT_ERR_TRUNCATED || noffset == -FDT_ERR_BADSTRUCTURE) {
