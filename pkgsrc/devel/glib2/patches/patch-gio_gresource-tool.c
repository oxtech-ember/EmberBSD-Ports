$NetBSD: patch-gio_gresource-tool.c,v 1.2 2019/06/03 09:53:50 prlw1 Exp $

Solaris fix

--- gio/gresource-tool.c.orig
+++ gio/gresource-tool.c
@@ -31,6 +31,11 @@
 #include <locale.h>
 
 #ifdef HAVE_LIBELF
+/* Solaris native libelf does not support largefile in 32-bit mode */
+#  if defined(__sun) && defined(__i386)
+#    undef  _FILE_OFFSET_BITS
+#    define _FILE_OFFSET_BITS   32
+#  endif
 #include <libelf.h>
 #include <gelf.h>
 #endif
