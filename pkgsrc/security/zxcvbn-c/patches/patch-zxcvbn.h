# Expose the matching detailed password limit to consumers.
# Origin: EmberBSD.
--- zxcvbn.h.orig
+++ zxcvbn.h
@@ -24,6 +24,11 @@
  *
  **********************************************************************************/
 
+/* Maximum password bytes subject to detailed matching. */
+#ifndef ZXCVBN_DETAIL_LEN
+#define ZXCVBN_DETAIL_LEN 100
+#endif
+
 /* If this is defined, the dictiononary data is read from file. When undefined */
 /* dictionary data is included in the source code. */
 /*#define USE_DICT_FILE */
