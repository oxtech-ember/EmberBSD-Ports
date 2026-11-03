--- bmm150_defs.h.orig
+++ bmm150_defs.h
@@ -44,17 +44,20 @@
 /******************************************************************************/
 /*! @name       Header includes                           */
 /******************************************************************************/
-#ifdef __KERNEL__
+#if defined(_KERNEL) && !defined(__KERNEL__)
+#include <sys/param.h>
+#elif defined(__KERNEL__)
 #include <linux/types.h>
 #else
 #include <stdint.h>
 #include <stddef.h>
+#include <limits.h>
 #endif
 
 /******************************************************************************/
 /*! @name       Common macros                         */
 /******************************************************************************/
-#ifdef __KERNEL__
+#if defined(_KERNEL) || defined(__KERNEL__)
 #if (LONG_MAX) > 0x7fffffff
 #define __have_long64  1
 #elif (LONG_MAX) == 0x7fffffff
