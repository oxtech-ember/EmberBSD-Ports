EmberBSD local portability repair, AI-assisted; not submitted upstream.
Include the NetBSD declaration of _exit used by the signal handler.

--- source/compiler/aslmain.c.orig
+++ source/compiler/aslmain.c
@@ -17,6 +17,9 @@
 #include "acapps.h"
 #include "acdisasm.h"
 #include <signal.h>
+#ifdef __NetBSD__
+#include <unistd.h> /* _exit */
+#endif
 
 #define _COMPONENT          ACPI_COMPILER
         ACPI_MODULE_NAME    ("aslmain")
