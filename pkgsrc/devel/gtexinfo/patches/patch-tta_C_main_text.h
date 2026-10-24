$NetBSD$

Let the compiler check the printf-like Texinfo helpers.

--- tta/C/main/text.h.orig
+++ tta/C/main/text.h
@@ -19,6 +19,14 @@
 #include <stddef.h>
 #include <stdarg.h>
 
+/* Let compilers check printf-like format strings and arguments. */
+#if defined __GNUC__
+# define TXI_PRINTF_FORMAT(fmt, arg) \
+  __attribute__ ((__format__ (__printf__, fmt, arg)))
+#else
+# define TXI_PRINTF_FORMAT(fmt, arg)
+#endif
+
 int xvasprintf (char **ptr, const char *format, va_list ap);
 
 typedef struct TEXT {
@@ -30,7 +38,8 @@
 void text_init (TEXT *t);
 void text_append (TEXT *t, const char *s);
 void text_append_n (TEXT *t, const char *s, size_t len);
-void text_printf (TEXT *t, const char *format, ...);
+void text_printf (TEXT *t, const char *format, ...)
+  TXI_PRINTF_FORMAT (2, 3);
 void text_alloc (TEXT *t, size_t len);
 void text_reset (TEXT *t);
 
