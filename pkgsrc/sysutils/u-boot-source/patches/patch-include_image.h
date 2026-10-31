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
