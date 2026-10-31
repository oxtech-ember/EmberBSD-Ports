$NetBSD$

Adapt libgit2 to the shared Git xdiff source.

--- src/libgit2/diff_xdiff.h.orig
+++ src/libgit2/diff_xdiff.h
@@ -10,6 +10,7 @@
 #include "common.h"
 
 #include "diff.h"
+#include "git-xdiff.h"
 #include "xdiff.h"
 #include "patch_generate.h"
 
