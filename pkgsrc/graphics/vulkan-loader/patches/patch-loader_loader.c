$NetBSD$

Origin: EmberBSD contributors (AI-assisted).
Resolve built-in Darwin search directories from the installed library.

--- loader/loader.c.orig
+++ loader/loader.c
@@ -3322,8 +3322,13 @@
 }
 
 // NOLINTNEXTLINE(bugprone-easily-swappable-parameters) - no safer ordering for these two path string parameters
+#if defined(__APPLE__)
+VkResult copy_search_paths(const struct loader_instance *inst, const char *cur_path, const char *relative_path,
+                           size_t relative_path_size, struct loader_string_list *search_paths, bool configured) {
+#else
 VkResult copy_data_file_info(const struct loader_instance *inst, const char *cur_path, const char *relative_path,
                              size_t relative_path_size, struct loader_string_list *search_paths) {
+#endif
     if (NULL != cur_path) {
         uint32_t start = 0;
         uint32_t stop = 0;
@@ -3336,7 +3341,31 @@
             while (cur_path[stop] != PATH_SEPARATOR && cur_path[stop] != '\0') {
                 stop++;
             }
-            const size_t s = stop - start;
+            const char *path = cur_path + start;
+            size_t s = stop - start;
+#if defined(__APPLE__)
+            static const char token[] = "@loader_path/";
+            char image[PATH_MAX];
+            if (configured && s >= sizeof(token) - 1 && memcmp(path, token, sizeof(token) - 1) == 0) {
+                Dl_info info;
+                char *name;
+                if (!dladdr((const void *)&copy_search_paths, &info) || !info.dli_fname ||
+                    !realpath(info.dli_fname, image) || !(name = strrchr(image, '/'))) {
+                    start = stop;
+                    continue;
+                }
+                size_t dir_len = (size_t)(name + 1 - image);
+                size_t tail_len = s - (sizeof(token) - 1);
+                if (tail_len >= sizeof(image) - dir_len) {
+                    start = stop;
+                    continue;
+                }
+                memcpy(name + 1, path + sizeof(token) - 1, tail_len);
+                image[dir_len + tail_len] = '\0';
+                path = image;
+                s = dir_len + tail_len;
+            }
+#endif
             if (s) {
                 // space enough for base path, relative path, path separator, and null terminator
                 size_t new_str_len = s + relative_path_size + 2;
@@ -3345,7 +3374,7 @@
                 if (NULL == new_str) {
                     return VK_ERROR_OUT_OF_HOST_MEMORY;
                 }
-                memcpy(new_str, &cur_path[start], s);
+                memcpy(new_str, path, s);
                 new_str[s] = '\0';
 
                 // If this is a specific JSON file, just add it and don't add any
@@ -3374,6 +3403,13 @@
     }
     return VK_SUCCESS;
 }
+
+#if defined(__APPLE__)
+VkResult copy_data_file_info(const struct loader_instance *inst, const char *cur_path, const char *relative_path,
+                             size_t relative_path_size, struct loader_string_list *search_paths) {
+    return copy_search_paths(inst, cur_path, relative_path, relative_path_size, search_paths, false);
+}
+#endif
 
 // If the file found is a manifest file name, add it to the end of out_files manifest list.
 VkResult add_if_manifest_file(const struct loader_instance *inst, const char *file_name, struct loader_string_list *out_files) {
@@ -3541,7 +3577,8 @@
     char *xdg_config_dirs = loader_secure_getenv("XDG_CONFIG_DIRS", inst);
 
 #if !defined(__Fuchsia__) && !defined(__QNX__)
-    if (NULL == xdg_config_dirs || '\0' == xdg_config_dirs[0]) {
+    const bool default_config = NULL == xdg_config_dirs || '\0' == xdg_config_dirs[0];
+    if (default_config) {
         xdg_config_dirs = FALLBACK_CONFIG_DIRS;
     }
 #endif
@@ -3550,7 +3587,8 @@
     char *xdg_data_dirs = loader_secure_getenv("XDG_DATA_DIRS", inst);
 
 #if !defined(__Fuchsia__) && !defined(__QNX__)
-    if (NULL == xdg_data_dirs || '\0' == xdg_data_dirs[0]) {
+    const bool default_data = NULL == xdg_data_dirs || '\0' == xdg_data_dirs[0];
+    if (default_data) {
         xdg_data_dirs = FALLBACK_DATA_DIRS;
     }
 #endif
@@ -3758,11 +3796,11 @@
                         goto out;
                     }
                 }
-                vk_result = copy_data_file_info(inst, xdg_config_dirs, relative_location, rel_size, &search_paths);
+                vk_result = copy_search_paths(inst, xdg_config_dirs, relative_location, rel_size, &search_paths, default_config);
                 if (VK_SUCCESS != vk_result) {
                     goto out;
                 }
-                vk_result = copy_data_file_info(inst, SYSCONFDIR, relative_location, rel_size, &search_paths);
+                vk_result = copy_search_paths(inst, SYSCONFDIR, relative_location, rel_size, &search_paths, true);
                 if (VK_SUCCESS != vk_result) {
                     goto out;
                 }
@@ -3780,7 +3818,7 @@
                         goto out;
                     }
                 }
-                vk_result = copy_data_file_info(inst, xdg_data_dirs, relative_location, rel_size, &search_paths);
+                vk_result = copy_search_paths(inst, xdg_data_dirs, relative_location, rel_size, &search_paths, default_data);
                 if (VK_SUCCESS != vk_result) {
                     goto out;
                 }
