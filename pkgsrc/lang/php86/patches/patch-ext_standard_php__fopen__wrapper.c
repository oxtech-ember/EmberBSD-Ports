$NetBSD: patch-ext_standard_php__fopen__wrapper.c,v 1.1 2026/01/08 13:38:00 taca Exp $

Add build-time disable option for dangerous php://filter URL

php://filter URL is a feature documented here:
http://php.net/manual/en/wrappers.php.php

Unfortunately, it allows remote control of include() behavior
beyond what many developpers expected, enabling easy dump of
PHP source files. The administrator may want to disable the
feature for security sake, and this patch makes that possible.

--- ext/standard/php_fopen_wrapper.c.orig
+++ ext/standard/php_fopen_wrapper.c
@@ -367,6 +367,7 @@
 				"[%d]: %s", fildes_ori, errno, strerror(errno));
 			return NULL;
 		}
+#ifndef DISABLE_FILTER_URL
 	} else if (!strncasecmp(path, "filter/", 7)) {
 		/* Save time/memory when chain isn't specified */
 		if (strchr(mode, 'r') || strchr(mode, '+')) {
@@ -422,6 +423,7 @@
 		}
 
 		return stream;
+#endif /* !DISABLE_FILTER_URL */
 	} else {
 		/* invalid php://thingy */
 		php_stream_wrapper_warn(wrapper, context, options,
