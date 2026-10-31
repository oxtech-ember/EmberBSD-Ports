$NetBSD$

Adapt libgit2 to the shared Git xdiff source.

--- src/libgit2/diff_xdiff.c.orig
+++ src/libgit2/diff_xdiff.c
@@ -199,6 +199,7 @@
 	git_xdiff_output *xo = (git_xdiff_output *)output;
 	git_xdiff_info info;
 	git_diff_find_context_payload findctxt;
+	int error;
 
 	memset(&info, 0, sizeof(info));
 	info.patch = patch;
@@ -223,12 +224,12 @@
 	    git_patch_generated_new_data(&info.xd_new_data.ptr, &info.xd_new_data.size, patch) < 0)
 		return -1;
 
-	xdl_diff(&info.xd_old_data, &info.xd_new_data,
+	error = xdl_diff(&info.xd_old_data, &info.xd_new_data,
 		&xo->params, &xo->config, &xo->callback);
 
 	git_diff_find_context_clear(&findctxt);
 
-	return xo->output.error;
+	return xo->output.error ? xo->output.error : error;
 }
 
 void git_xdiff_init(git_xdiff_output *xo, const git_diff_options *opts)
