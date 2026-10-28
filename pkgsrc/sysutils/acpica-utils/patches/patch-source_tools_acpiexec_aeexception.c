EmberBSD local portability repair, AI-assisted; not submitted upstream.
Include the NetBSD declaration of _exit used by the signal handler.

--- source/tools/acpiexec/aeexception.c.orig
+++ source/tools/acpiexec/aeexception.c
@@ -12,6 +12,10 @@
  *****************************************************************************/
 
 #include "aecommon.h"
+
+#ifdef __NetBSD__
+#include <unistd.h> /* _exit */
+#endif
 
 #define _COMPONENT          ACPI_TOOLS
         ACPI_MODULE_NAME    ("aeexception")
