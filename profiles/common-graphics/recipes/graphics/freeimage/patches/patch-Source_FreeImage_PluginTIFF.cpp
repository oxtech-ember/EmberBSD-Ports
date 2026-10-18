Origin: EmberBSD (AI-assisted), common Unix ABI and current system codecs.

--- Source/FreeImage/PluginTIFF.cpp.orig
+++ Source/FreeImage/PluginTIFF.cpp
@@ -41,7 +41,11 @@
 #include "Utilities.h"
 #include <tiffio.h>
 #include "../Metadata/FreeImageTag.h"
+#ifdef FREEIMAGE_SYSTEM_OPENEXR
+#include <Imath/half.h>
+#else
 #include "../OpenEXR/Half/half.h"
+#endif
 
 #include "FreeImageIO.h"
 #include "PSDParser.h"
