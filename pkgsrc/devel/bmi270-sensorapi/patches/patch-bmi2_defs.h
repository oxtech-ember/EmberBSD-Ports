--- bmi2_defs.h.orig
+++ bmi2_defs.h
@@ -42,7 +42,10 @@
 /******************************************************************************/
 /*! @name       Header includes                           */
 /******************************************************************************/
-#ifdef __KERNEL__
+#if defined(_KERNEL) && !defined(__KERNEL__)
+#include <sys/param.h>
+#include <sys/types.h>
+#elif defined(__KERNEL__)
 #include <linux/types.h>
 #include <linux/kernel.h>
 #else
