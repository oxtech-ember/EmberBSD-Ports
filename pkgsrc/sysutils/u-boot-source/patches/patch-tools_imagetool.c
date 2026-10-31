$NetBSD$

--- a/tools/imagetool.c
+++ b/tools/imagetool.c
@@ -8,6 +8,10 @@
 #include "imagetool.h"
 
 #include <image.h>
+
+#ifdef __MACH__
+struct image_type_params **__start_image_type, **__stop_image_type;
+#endif
 
 struct image_type_params *imagetool_get_type(int type)
 {
