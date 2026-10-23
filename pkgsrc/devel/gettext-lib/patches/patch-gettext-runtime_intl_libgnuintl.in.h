$NetBSD$

Use the existing locale macro mappings for GCC C on Darwin.
Keep both function-address and call redirection to the libintl symbols.
Keep C++ and other target platforms unchanged.
Origin: EmberBSD contributors (AI-assisted); not submitted upstream.
The upstream LGPL-2.1-or-later license and authorship are unchanged.

--- gettext-runtime/intl/libgnuintl.in.h.orig
+++ gettext-runtime/intl/libgnuintl.in.h
@@ -1093,7 +1093,9 @@
   return libintl_setlocale (__category, __locale);
 }
 #  elif !defined _INTL_NO_DEFINE_MACRO_SETLOCALE
-#   ifdef _INTL_REDIRECT_MACROS
+#   if defined _INTL_REDIRECT_MACROS \
+       || (defined _INTL_REDIRECT_ASM && defined __APPLE__ && defined __MACH__ \
+           && defined __GNUC__ && !defined __clang__ && !defined __cplusplus)
 #    undef setlocale
 #    define setlocale libintl_setlocale
 #   endif
@@ -1121,7 +1123,9 @@
   return libintl_newlocale (__category_mask, __name, __base);
 }
 #   elif !defined _INTL_NO_DEFINE_MACRO_NEWLOCALE
-#    ifdef _INTL_REDIRECT_MACROS
+#    if defined _INTL_REDIRECT_MACROS \
+        || (defined _INTL_REDIRECT_ASM && defined __APPLE__ && defined __MACH__ \
+            && defined __GNUC__ && !defined __clang__ && !defined __cplusplus)
 #     undef newlocale
 #     define newlocale libintl_newlocale
 #    endif
