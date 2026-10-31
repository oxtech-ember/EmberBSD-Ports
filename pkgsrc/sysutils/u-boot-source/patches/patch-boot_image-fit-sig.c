$NetBSD$

--- a/boot/image-fit-sig.c
+++ b/boot/image-fit-sig.c
@@ -66,7 +66,7 @@
 static int fit_image_setup_verify(struct image_sign_info *info,
 				  const void *fit, int noffset,
 				  const void *key_blob, int required_keynode,
-				  char **err_msgp)
+				  char **err_msgp, bool quiet)
 {
 	const char *algo_name;
 	const char *padding_name;
@@ -94,7 +94,8 @@
 	info->padding = image_get_padding_algo(padding_name);
 	info->fdt_blob = key_blob;
 	info->required_keynode = required_keynode;
-	printf("%s:%s", algo_name, info->keyname);
+	if (!quiet)
+		printf("%s:%s", algo_name, info->keyname);
 
 	if (!info->checksum || !info->crypto) {
 		*err_msgp = "Unknown signature algorithm";
@@ -104,9 +105,9 @@
 	return 0;
 }
 
-int fit_image_check_sig(const void *fit, int noffset, const void *data,
+int fit_image_check_sig_quiet(const void *fit, int noffset, const void *data,
 			size_t size, const void *key_blob, int required_keynode,
-			char **err_msgp)
+			char **err_msgp, bool quiet)
 {
 	struct image_sign_info info;
 	struct image_region region;
@@ -115,7 +116,7 @@
 
 	*err_msgp = NULL;
 	if (fit_image_setup_verify(&info, fit, noffset, key_blob,
-				   required_keynode, err_msgp))
+				   required_keynode, err_msgp, quiet))
 		return -1;
 
 	if (fit_image_hash_get_value(fit, noffset, &fit_value,
@@ -135,9 +136,18 @@
 	return 0;
 }
 
+int fit_image_check_sig(const void *fit, int noffset, const void *data,
+			size_t size, const void *key_blob, int required_keynode,
+			char **err_msgp)
+{
+	return fit_image_check_sig_quiet(fit, noffset, data, size, key_blob,
+					 required_keynode, err_msgp, false);
+}
+
 static int fit_image_verify_sig(const void *fit, int image_noffset,
 				const char *data, size_t size,
-				const void *key_blob, int key_offset)
+				const void *key_blob, int key_offset, bool quiet,
+				bool *sig_failed)
 {
 	int noffset;
 	char *err_msg = "";
@@ -158,12 +168,16 @@
 		}
 		if (!strncmp(name, FIT_SIG_NODENAME,
 			     strlen(FIT_SIG_NODENAME))) {
-			ret = fit_image_check_sig(fit, noffset, data, size,
-						  key_blob, -1, &err_msg);
+			ret = fit_image_check_sig_quiet(fit, noffset, data, size,
+						  key_blob, -1, &err_msg, quiet);
 			if (ret) {
-				puts("- ");
+				if (quiet && sig_failed)
+					*sig_failed = true;
+				if (!quiet)
+					puts("- ");
 			} else {
-				puts("+ ");
+				if (!quiet)
+					puts("+ ");
 				verified = 1;
 				break;
 			}
@@ -184,9 +198,10 @@
 	return -1;
 }
 
-int fit_image_verify_required_sigs(const void *fit, int image_noffset,
+int fit_image_verify_required_sigs_quiet(const void *fit, int image_noffset,
 				   const char *data, size_t size,
-				   const void *key_blob, int *no_sigsp)
+				   const void *key_blob, int *no_sigsp, bool quiet,
+				   bool *sig_failed)
 {
 	int verify_count = 0;
 	int noffset;
@@ -215,7 +230,7 @@
 		if (!required || strcmp(required, "image"))
 			continue;
 		ret = fit_image_verify_sig(fit, image_noffset, data, size,
-					   key_blob, noffset);
+					   key_blob, noffset, quiet, sig_failed);
 		if (ret) {
 			printf("Failed to verify required signature '%s'\n",
 			       fit_get_name(key_blob, noffset, NULL));
@@ -228,6 +243,13 @@
 		*no_sigsp = 0;
 
 	return 0;
+}
+
+int fit_image_verify_required_sigs(const void *fit, int image_noffset,
+		const char *data, size_t size, const void *key_blob, int *no_sigsp)
+{
+	return fit_image_verify_required_sigs_quiet(fit, image_noffset, data,
+					     size, key_blob, no_sigsp, false, NULL);
 }
 
 /**
@@ -465,7 +487,7 @@
  */
 static int fit_config_check_sig(const void *fit, int noffset, int conf_noffset,
 				const void *key_blob, int required_keynode,
-				char **err_msgp)
+				char **err_msgp, bool quiet)
 {
 	static char * const exc_prop[] = {
 		FIT_DATA_PROP,
@@ -490,7 +512,7 @@
 	      fit_get_name(key_blob, required_keynode, NULL));
 	*err_msgp = NULL;
 	if (fit_image_setup_verify(&info, fit, noffset, key_blob,
-				   required_keynode, err_msgp))
+				   required_keynode, err_msgp, quiet))
 		return -1;
 
 	if (fit_image_hash_get_value(fit, noffset, &fit_value,
@@ -603,7 +625,8 @@
  *	configuration node has an invalid name
  */
 static int fit_config_verify_key(const void *fit, int conf_noffset,
-				 const void *key_blob, int key_offset)
+				 const void *key_blob, int key_offset, bool quiet,
+				bool *sig_failed)
 {
 	int noffset;
 	char *err_msg = "No 'signature' subnode found";
@@ -618,11 +641,15 @@
 			     strlen(FIT_SIG_NODENAME))) {
 			ret = fit_config_check_sig(fit, noffset, conf_noffset,
 						   key_blob, key_offset,
-						   &err_msg);
+						   &err_msg, quiet);
 			if (ret) {
-				puts("- ");
+				if (quiet && sig_failed)
+					*sig_failed = true;
+				if (!quiet)
+					puts("- ");
 			} else {
-				puts("+ ");
+				if (!quiet)
+					puts("+ ");
 				verified = 1;
 				break;
 			}
@@ -638,8 +665,13 @@
 		return 0;
 
 error:
-	printf(" error!\n%s for '%s' config node\n",
-	       err_msg, fit_get_name(fit, conf_noffset, NULL));
+	if (quiet) {
+		if (sig_failed)
+			*sig_failed = true;
+	} else {
+		printf(" error!\n%s for '%s' config node\n",
+		       err_msg, fit_get_name(fit, conf_noffset, NULL));
+	}
 	return -EPERM;
 }
 
@@ -657,7 +689,8 @@
  *	configuration node has an invalid name
  */
 static int fit_config_verify_required_keys(const void *fit, int conf_noffset,
-					   const void *key_blob)
+					   const void *key_blob, bool quiet,
+					   bool *sig_failed)
 {
 	const char *name = fit_get_name(fit, conf_noffset, NULL);
 	int noffset;
@@ -716,7 +749,7 @@
 		reqd_sigs++;
 
 		ret = fit_config_verify_key(fit, conf_noffset, key_blob,
-					    noffset);
+					    noffset, quiet, sig_failed);
 		if (ret) {
 			if (reqd_policy_all) {
 				printf("Failed to verify required signature '%s'\n",
@@ -741,11 +774,16 @@
 int fit_config_verify_with_key_blob(const void *fit, int conf_noffset,
 				    const void *key_blob)
 {
-	return fit_config_verify_required_keys(fit, conf_noffset, key_blob);
+	return fit_config_verify_required_keys(fit, conf_noffset, key_blob, false, NULL);
 }
 
+int fit_config_verify_quiet(const void *fit, int conf_noffset, bool quiet,
+			    bool *sig_failed)
+{
+	return fit_config_verify_required_keys(fit, conf_noffset, gd_fdt_blob(), quiet, sig_failed);
+}
+
 int fit_config_verify(const void *fit, int conf_noffset)
 {
-	return fit_config_verify_with_key_blob(fit, conf_noffset,
-					       gd_fdt_blob());
+	return fit_config_verify_quiet(fit, conf_noffset, false, NULL);
 }
