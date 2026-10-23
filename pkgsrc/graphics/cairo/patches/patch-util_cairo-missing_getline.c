$NetBSD: patch-util_cairo-missing_getline.c,v 1.1 2023/11/14 13:48:19 wiz Exp $

The variable name is self-explanatory :)

--- util/cairo-missing/getline.c.orig
+++ util/cairo-missing/getline.c
@@ -87,4 +87,6 @@
     return ret;
 }
 #undef GETLINE_BUFFER_SIZE
+#else
+int solaris_ld_requires_at_least_one_symbol = 0;
 #endif
