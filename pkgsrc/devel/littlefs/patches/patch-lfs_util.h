$NetBSD$

--- lfs_util.h.orig
+++ lfs_util.h
@@ -39,15 +39,22 @@
 #endif
 
 // System includes
+#if defined(_KERNEL) && defined(__NetBSD__)
+#include <sys/types.h>
+#include <sys/stdint.h>
+#include <sys/inttypes.h>
+#include <sys/systm.h>
+#else
 #include <stdint.h>
 #include <stdbool.h>
 #include <string.h>
 #include <inttypes.h>
+#endif
 
 #ifndef LFS_NO_MALLOC
 #include <stdlib.h>
 #endif
-#ifndef LFS_NO_ASSERT
+#if !defined(LFS_NO_ASSERT) && !defined(LFS_ASSERT)
 #include <assert.h>
 #endif
 #if !defined(LFS_NO_DEBUG) || \
