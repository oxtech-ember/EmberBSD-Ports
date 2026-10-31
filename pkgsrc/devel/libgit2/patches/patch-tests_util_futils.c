$NetBSD$

Exercise checked checkout removal without traversing symlink parents.

--- tests/util/futils.c.orig
+++ tests/util/futils.c
@@ -113,3 +113,43 @@
 	git_str_dispose(&path);
 #endif
 }
+
+void test_futils__rmdir_parent_symlink(void)
+{
+	struct stat st;
+	git_str base = GIT_STR_INIT, path = GIT_STR_INIT;
+
+	if (!git_fs_path_supports_symlinks("futils"))
+		cl_skip();
+
+	cl_git_fail(git_futils_rmdir_r("futils/missing", NULL, GIT_RMDIR_CHECK_PARENTS));
+	cl_must_pass(p_mkdir("futils/base", 0777));
+	cl_must_pass(p_mkdir("futils/outside", 0777));
+	cl_must_pass(p_mkdir("futils/base2", 0777));
+	cl_git_mkfile("futils/outside/sentinel", "keep");
+	cl_must_pass(p_symlink("../outside", "futils/base/link"));
+	cl_git_pass(git_fs_path_prettify_dir(&base, "futils/base", NULL));
+	cl_git_pass(git_fs_path_prettify_dir(&path, "futils/outside", NULL));
+	cl_git_fail(git_futils_rmdir_r(path.ptr, base.ptr, GIT_RMDIR_REMOVE_FILES | GIT_RMDIR_CHECK_PARENTS));
+	cl_git_pass(git_str_joinpath(&path, path.ptr, "missing"));
+	cl_git_pass(git_futils_rmdir_r(path.ptr, base.ptr, GIT_RMDIR_REMOVE_FILES));
+	cl_git_pass(git_fs_path_prettify_dir(&path, "futils/base2", NULL));
+	cl_git_fail(git_futils_rmdir_r(path.ptr, base.ptr, GIT_RMDIR_REMOVE_FILES | GIT_RMDIR_CHECK_PARENTS));
+	cl_git_fail(git_futils_rmdir_r("../outside/sentinel", base.ptr, GIT_RMDIR_REMOVE_FILES | GIT_RMDIR_CHECK_PARENTS));
+	cl_assert_equal_file("keep", 4, "futils/outside/sentinel");
+	git_str_clear(&path);
+	cl_git_pass(git_str_joinpath(&path, base.ptr, "link/sentinel"));
+	cl_git_fail(git_futils_rmdir_r(path.ptr, base.ptr, GIT_RMDIR_REMOVE_FILES | GIT_RMDIR_CHECK_PARENTS));
+	git_str_dispose(&path);
+	git_str_dispose(&base);
+
+	cl_git_fail(git_futils_rmdir_r("link/sentinel", "futils/base", GIT_RMDIR_REMOVE_FILES | GIT_RMDIR_CHECK_PARENTS));
+	cl_assert_equal_file("keep", 4, "futils/outside/sentinel");
+	cl_must_pass(p_lstat_posixly("futils/base/link", &st));
+	cl_assert(S_ISLNK(st.st_mode));
+
+	cl_git_pass(git_futils_rmdir_r("link/sentinel", "futils/base",
+		GIT_RMDIR_REMOVE_FILES | GIT_RMDIR_REMOVE_BLOCKERS | GIT_RMDIR_CHECK_PARENTS));
+	cl_assert_equal_file("keep", 4, "futils/outside/sentinel");
+	cl_assert(p_lstat_posixly("futils/base/link", &st) < 0);
+}
