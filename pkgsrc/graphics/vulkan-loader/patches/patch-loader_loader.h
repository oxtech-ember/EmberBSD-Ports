$NetBSD$

Origin: EmberBSD contributors (AI-assisted).
Share the configured search path resolver with loader settings.

--- loader/loader.h.orig
+++ loader/loader.h
@@ -234,6 +234,14 @@
 
 TEST_FUNCTION_EXPORT VkStringErrorFlags vk_string_validate(const int max_length, const char *utf8);
 char *loader_get_next_path(char *path);
+#if defined(__APPLE__)
+// Expand library-relative paths only for directories from the build configuration.
+VkResult copy_search_paths(const struct loader_instance *inst, const char *paths, const char *relative_path,
+                           size_t relative_path_size, struct loader_string_list *search_paths, bool configured);
+#else
+#define copy_search_paths(inst, paths, relative, size, list, configured) copy_data_file_info(inst, paths, relative, size, list)
+#endif
+
 VkResult add_if_manifest_file(const struct loader_instance *inst, const char *file_name, struct loader_string_list *out_files);
 VkResult prepend_if_manifest_file(const struct loader_instance *inst, const char *file_name, struct loader_string_list *out_files);
 VkResult add_data_files(const struct loader_instance *inst, struct loader_string_list *search_paths,
