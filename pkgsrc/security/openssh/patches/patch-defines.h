$NetBSD: patch-defines.h,v 1.6 2025/02/18 09:33:07 wiz Exp $

Provide the NetBSD const cast for portable builds and define login record paths.

--- defines.h.orig	2015-08-21 04:49:03.000000000 +0000
+++ defines.h
@@ -24,6 +24,11 @@
 
 #ifndef _DEFINES_H
 #define _DEFINES_H
+
+/* NetBSD const-correct interfaces also serve portable OpenSSH builds. */
+#ifndef __UNCONST
+# define __UNCONST(a) ((void *)(uintptr_t)(const void *)(a))
+#endif
 
 /* Constants */
 
@@ -721,6 +726,24 @@ struct winsize {
 #    endif
 #  endif
 #endif
+#ifndef UTMPX_FILE
+#  ifdef _PATH_UTMPX
+#    define UTMPX_FILE _PATH_UTMPX
+#  else
+#    ifdef CONF_UTMPX_FILE
+#      define UTMPX_FILE CONF_UTMPX_FILE
+#    endif
+#  endif
+#endif
+#ifndef WTMPX_FILE
+#  ifdef _PATH_WTMPX
+#    define WTMPX_FILE _PATH_WTMPX
+#  else
+#    ifdef CONF_WTMPX_FILE
+#      define WTMPX_FILE CONF_WTMPX_FILE
+#    endif
+#  endif
+#endif
 /* pick up the user's location for lastlog if given */
 #ifndef LASTLOG_FILE
 #  ifdef _PATH_LASTLOG
