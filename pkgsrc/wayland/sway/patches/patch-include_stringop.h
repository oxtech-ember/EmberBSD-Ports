$NetBSD$

Origin: EmberBSD (AI-assisted).
Declare va_list in the header that uses it. NetBSD does not expose this type
through an unrelated standard header.

--- include/stringop.h.orig
+++ include/stringop.h
@@ -1,6 +1,7 @@
 #ifndef _SWAY_STRINGOP_H
 #define _SWAY_STRINGOP_H
 
+#include <stdarg.h>
 #include <stdbool.h>
 #include <stddef.h>
 #include "list.h"
