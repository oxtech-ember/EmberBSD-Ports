$NetBSD$

Retain the pkgsrc Unix declarations for the gzip file API. The package
uses its libtool Makefile rather than upstream configure, which would
otherwise select unistd.h. GCC16 requires the proper POSIX declarations.

Origin: pkgsrc devel/zlib/files/gzguts.h at
fff4deb639a1a640476203c80f752fb77b6cb14b. Rebased by EmberBSD (AI-assisted).

--- gzguts.h.orig
+++ gzguts.h
@@ -41,6 +41,7 @@
 #  define _POSIX_C_SOURCE 200112L
 #endif
 #include <fcntl.h>
+#include <unistd.h>
 
 #ifdef _WIN32
 #  include <stddef.h>
