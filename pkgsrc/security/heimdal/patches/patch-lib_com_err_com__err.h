$NetBSD$

The public header is installed with com_right.h as a sibling under include/krb5.
Use quoted lookup so the installed public header can find its sibling without
requiring consumers to add a second include directory.

--- lib/com_err/com_err.h.orig
+++ lib/com_err/com_err.h
@@ -36,7 +36,7 @@
 #ifndef __COM_ERR_H__
 #define __COM_ERR_H__
 
-#include <com_right.h>
+#include "com_right.h"
 #include <stdarg.h>
 
 #if !defined(__GNUC__) && !defined(__attribute__)
