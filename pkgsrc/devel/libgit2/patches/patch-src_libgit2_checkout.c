$NetBSD$

Protect sequential checkout removal from detected parent symlinks.

--- src/libgit2/checkout.c.orig
+++ src/libgit2/checkout.c
@@ -1826,7 +1826,8 @@
 	size_t i;
 	git_str *fullpath;
 	uint32_t flg = GIT_RMDIR_EMPTY_PARENTS |
-		GIT_RMDIR_REMOVE_FILES | GIT_RMDIR_REMOVE_BLOCKERS;
+		GIT_RMDIR_REMOVE_FILES | GIT_RMDIR_REMOVE_BLOCKERS |
+		GIT_RMDIR_CHECK_PARENTS;
 
 	if (data->opts.checkout_strategy & GIT_CHECKOUT_SKIP_LOCKED_DIRECTORIES)
 		flg |= GIT_RMDIR_SKIP_NONEMPTY;
