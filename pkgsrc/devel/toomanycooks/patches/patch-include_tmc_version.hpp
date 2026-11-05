# $NetBSD$

Match version macros to the upstream 1.6.1 release tag.

--- include/tmc/version.hpp.orig
+++ include/tmc/version.hpp
@@ -16,8 +16,8 @@
 
 /// The patch version of TooManyCooks. Patch versions > 0 are used exclusively
 /// for bugfixes that are backward-compatible (no breaking API changes).
-#define TMC_VERSION_PATCH 0
+#define TMC_VERSION_PATCH 1
 
 /// This number is updated to (MAJOR<<16) + (MINOR<<8) + PATCH for each new
 /// release tagged vMAJOR.MINOR.PATCH
-#define TMC_VERSION 0x00010600
+#define TMC_VERSION 0x00010601
