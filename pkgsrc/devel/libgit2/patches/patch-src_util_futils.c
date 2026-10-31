$NetBSD$

Protect sequential checkout removal from detected parent symlinks.

--- src/util/futils.c.orig
+++ src/util/futils.c
@@ -852,6 +852,67 @@
 	return error;
 }
 
+/* Check from the trusted base outward before looking up a child path. */
+static int futils__rmdir_parent_blockers(git_str *path, const char *base,
+	uint32_t flags)
+{
+	size_t i, baselen;
+	struct stat st;
+	int error, en;
+
+	if (!base || !*base) {
+		git_error_set(GIT_ERROR_INVALID, "removal base is required");
+		return -1;
+	}
+
+	baselen = strlen(base);
+	if (git_fs_path_equal_or_prefixed(base, path->ptr, NULL) == GIT_FS_PATH_NOTEQUAL) {
+		git_error_set(GIT_ERROR_INVALID, "removal path is outside its base");
+		return -1;
+	}
+
+	/* Never normalize a parent reference through a possible symlink. */
+	for (i = baselen; i < path->size; i++) {
+		if ((i == baselen || path->ptr[i - 1] == '/') &&
+		    path->ptr[i] == '.' && path->ptr[i + 1] == '.' &&
+		    (path->ptr[i + 2] == '/' || path->ptr[i + 2] == '\0')) {
+			git_error_set(GIT_ERROR_INVALID, "parent reference in removal path");
+			return -1;
+		}
+	}
+
+	for (i = baselen; i < path->size; i++) {
+		if (path->ptr[i] != '/' || i <= baselen)
+			continue;
+
+		path->ptr[i] = '\0';
+		error = p_lstat_posixly(path->ptr, &st);
+		en = errno;
+		if (error < 0) {
+			path->ptr[i] = '/';
+			if (en == ENOENT || en == ENOTDIR)
+				return 0;
+			return git_fs_path_set_error(en, path->ptr, "stat parent");
+		}
+
+		if (S_ISLNK(st.st_mode)) {
+			if ((flags & GIT_RMDIR_REMOVE_BLOCKERS) == 0) {
+				git_error_set(GIT_ERROR_OS, "refusing symlink parent '%s'", path->ptr);
+				error = -1;
+			} else if (p_unlink(path->ptr) < 0) {
+				error = git_fs_path_set_error(errno, path->ptr, "remove blocker");
+			} else {
+				error = GIT_ITEROVER;
+			}
+			path->ptr[i] = '/';
+			return error;
+		}
+		path->ptr[i] = '/';
+	}
+
+	return 0;
+}
+
 int git_futils_rmdir_r(
 	const char *path, const char *base, uint32_t flags)
 {
@@ -868,7 +929,10 @@
 	data.baselen = base ? strlen(base) : 0;
 	data.flags   = flags;
 
-	error = futils__rmdir_recurs_foreach(&data, &fullpath);
+	error = (flags & GIT_RMDIR_CHECK_PARENTS) ?
+		futils__rmdir_parent_blockers(&fullpath, base, flags) : 0;
+	if (!error)
+		error = futils__rmdir_recurs_foreach(&data, &fullpath);
 
 	/* remove now-empty parents if requested */
 	if (!error && (flags & GIT_RMDIR_EMPTY_PARENTS) != 0)
