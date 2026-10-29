Use the common zstd provider in hosted builds; retain the upstream freestanding path.

--- src/exr_zstd.c.orig
+++ src/exr_zstd.c
@@ -6,7 +6,15 @@
  */
 
 #include "exr_internal.h"
+#ifdef EXR_FREESTANDING
 #include "tinyexr_zstd.h"
+#else
+#include <zstd.h>
+#define tinyexr_zstd_compress ZSTD_compress
+#define tinyexr_zstd_decompress ZSTD_decompress
+#define tinyexr_zstd_compress_bound ZSTD_compressBound
+#define tinyexr_zstd_is_error ZSTD_isError
+#endif
 
 /* The freestanding decode path and the disabled encoder must travel together:
  * a freestanding build links the malloc-stubbed amalgamation, so encode cannot
