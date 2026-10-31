$NetBSD$

Protect sequential checkout removal from detected parent symlinks.

--- src/util/futils.h.orig
+++ src/util/futils.h
@@ -170,6 +170,9 @@
  *       if removing this item leaves them empty
  * * GIT_RMDIR_REMOVE_BLOCKERS - remove blocking file that causes ENOTDIR
  * * GIT_RMDIR_SKIP_ROOT       - don't remove root directory itself
+ * * GIT_RMDIR_CHECK_PARENTS  - require a base and reject or remove detected
+ *       symlink parents; absolute paths must be lexically beneath base;
+ *       this does not prevent concurrent replacement
  */
 typedef enum {
 	GIT_RMDIR_EMPTY_HIERARCHY = 0,
@@ -177,7 +180,8 @@
 	GIT_RMDIR_SKIP_NONEMPTY   = (1 << 1),
 	GIT_RMDIR_EMPTY_PARENTS   = (1 << 2),
 	GIT_RMDIR_REMOVE_BLOCKERS = (1 << 3),
-	GIT_RMDIR_SKIP_ROOT       = (1 << 4)
+	GIT_RMDIR_SKIP_ROOT       = (1 << 4),
+	GIT_RMDIR_CHECK_PARENTS  = (1 << 5)
 } git_futils_rmdir_flags;
 
 /**
