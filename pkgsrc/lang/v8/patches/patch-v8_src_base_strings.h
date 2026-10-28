$NetBSD: patch-deps_v8_src_base_strings.h,v 1.1 2022/03/30 06:52:33 adam Exp $

Keep stdarg.h for the global va_list used by V8 on NetBSD and other hosts.
Combines the pkgsrc Node and Chromium requirements in one include.

--- src/base/strings.h.orig	2022-02-08 12:37:48.000000000 +0000
+++ src/base/strings.h
@@ -8,6 +8,7 @@
 #include "src/base/base-export.h"
 #include "src/base/macros.h"
 #include "src/base/vector.h"
+#include <stdarg.h>
 
 namespace v8 {
 namespace base {
