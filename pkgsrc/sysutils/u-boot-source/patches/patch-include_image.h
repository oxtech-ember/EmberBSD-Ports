$NetBSD$

--- a/include/image.h
+++ b/include/image.h
@@ -16,7 +16,9 @@
 #define __IMAGE_H__
 
 #include "compiler.h"
+#ifndef USE_HOSTCC
 #include <asm/byteorder.h>
+#endif
 #include <stdbool.h>
 
 /* Define this to avoid #ifdefs later on */
@@ -1457,13 +1459,35 @@
 int fit_image_verify_with_data(const void *fit, int image_noffset,
 			       const void *key_blob, const void *data,
 			       size_t size);
+
+/*
+ * Quiet mode suppresses progress; nonfatal signature failures set sig_failed
+ * for the caller to report after the shared transport closes.  Required
+ * verification failures retain their return status and diagnostics.
+ */
+int fit_image_verify_with_data_quiet(const void *fit, int image_noffset,
+		const void *key_blob, const void *data, size_t size, bool quiet, bool *sig_failed);
+int fit_image_verify_required_sigs_quiet(const void *fit, int image_noffset,
+		const char *data, size_t size, const void *key_blob, int *no_sigsp,
+		bool quiet, bool *sig_failed);
+int fit_image_check_sig_quiet(const void *fit, int noffset, const void *data,
+		size_t size, const void *key_blob, int required_keynode,
+		char **err_msgp, bool quiet);
 
 int fit_image_verify(const void *fit, int noffset);
 #if CONFIG_IS_ENABLED(FIT_SIGNATURE)
 int fit_config_verify(const void *fit, int conf_noffset);
+int fit_config_verify_quiet(const void *fit, int conf_noffset, bool quiet,
+			    bool *sig_failed);
 int fit_config_verify_with_key_blob(const void *fit, int conf_noffset,
 				    const void *key_blob);
 #else
+static inline int fit_config_verify_quiet(const void *fit, int conf_noffset, bool quiet,
+			    bool *sig_failed)
+{
+	return 0;
+}
+
 static inline int fit_config_verify(const void *fit, int conf_noffset)
 {
 	return 0;
