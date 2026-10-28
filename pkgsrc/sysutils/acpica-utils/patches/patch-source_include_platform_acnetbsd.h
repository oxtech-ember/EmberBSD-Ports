Carry the pkgsrc compatibility fallback for older NetBSD.

--- source/include/platform/acnetbsd.h.orig
+++ source/include/platform/acnetbsd.h
@@ -80,4 +80,10 @@
 #define ACPI_USE_NATIVE_DIVIDE
 #define ACPI_USE_NATIVE_MATH64
 
+/* NetBSD versions prior to 7 lack sem_timedwait() in librt. */
+#include <sys/param.h>
+#if (__NetBSD_Version__ < 700000000)
+#define ACPI_USE_ALTERNATE_TIMEOUT
+#endif
+
 #endif /* __ACNETBSD_H__ */
