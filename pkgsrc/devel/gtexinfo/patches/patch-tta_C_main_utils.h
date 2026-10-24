$NetBSD$

Let the compiler check the printf-like Texinfo helpers.

--- tta/C/main/utils.h.orig
+++ tta/C/main/utils.h
@@ -24,6 +24,7 @@
 /* for S_ISDIR, S_IFDIR and S_IFMT */
 #include <sys/stat.h>
 
+#include "text.h"
 #include "command_ids.h"
 #include "tree_types.h"
 #include "global_commands_types.h"
@@ -120,7 +121,8 @@
 const char *txi_in_language_regions (register const char *str,
                                      register size_t len);
 
-int xasprintf (char **ptr, const char *template, ...);
+int xasprintf (char **ptr, const char *template, ...)
+  TXI_PRINTF_FORMAT (2, 3);
 
 size_t count_multibyte (const char *text);
 char *to_upper_or_lower_multibyte (const char *text, int lower_or_upper);
