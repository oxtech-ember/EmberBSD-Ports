$NetBSD$

Expose the NetBSD format-argument annotation for the logging adapter.
Origin: NetBSD NTP maintenance; adapted by EmberBSD (AI-assisted).
Upstream status: not submitted.

--- include/ntp_stdlib.h.orig
+++ include/ntp_stdlib.h
@@ -27,8 +27,10 @@
 
 #ifdef __GNUC__
 #define NTP_PRINTF(fmt, args) __attribute__((__format__(__printf__, fmt, args)))
+#define NTP_FORMAT_ARG(args) __attribute__((__format_arg__(args)))
 #else
 #define NTP_PRINTF(fmt, args)
+#define NTP_FORMAT_ARG(args)
 #endif
 
 extern	int	mprintf(const char *, ...) NTP_PRINTF(1, 2);
