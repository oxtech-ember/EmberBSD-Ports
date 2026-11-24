$NetBSD$

Origin: EmberBSD contributors (AI-assisted).
Use the installed Darwin package directories when looking for Vulkan settings.

--- loader/settings.c.orig
+++ loader/settings.c
@@ -474,6 +474,25 @@
     return VK_ERROR_INITIALIZATION_FAILED;
 }
 
+#if defined(__APPLE__)
+static VkResult check_settings_directories(const struct loader_instance* inst, const char* base, const char* suffix,
+                                           char** settings_file_path, bool configured) {
+    struct loader_string_list paths = {0};
+    VkResult res = copy_search_paths(inst, base, NULL, 0, &paths, configured);
+    if (res == VK_SUCCESS) {
+        res = VK_ERROR_INITIALIZATION_FAILED;
+        for (uint32_t i = 0; i < paths.count; ++i) {
+            res = check_if_settings_path_exists(inst, paths.list[i], suffix, settings_file_path);
+            if (res != VK_ERROR_INITIALIZATION_FAILED) break;
+        }
+    }
+    free_string_list(inst, &paths);
+    return res;
+}
+#else
+#define check_settings_directories(inst, base, suffix, out, configured) check_if_settings_path_exists(inst, base, suffix, out)
+#endif
+
 // Follow the logic of read_data_files_in_search_paths but only look for "/vulkan/loader_settings.d/" VK_LOADER_SETTINGS_FILENAME
 VkResult get_unix_settings_path(const struct loader_instance* inst, char** settings_file_path) {
     // First, get XDG env-vars we use. Don't need to worry about free'ing because on linux getenv is non-allocating
@@ -484,13 +503,15 @@
 
     // Use fallback directories for xdg_config_dirs and xdg_data_dirs if they are NULL.
 #if !defined(__Fuchsia__) && !defined(__QNX__)
-    if (NULL == xdg_config_dirs || '\0' == xdg_config_dirs[0]) {
+    const bool default_config = NULL == xdg_config_dirs || '\0' == xdg_config_dirs[0];
+    if (default_config) {
         xdg_config_dirs = FALLBACK_CONFIG_DIRS;
     }
 #endif
 
 #if !defined(__Fuchsia__) && !defined(__QNX__)
-    if (NULL == xdg_data_dirs || '\0' == xdg_data_dirs[0]) {
+    const bool default_data = NULL == xdg_data_dirs || '\0' == xdg_data_dirs[0];
+    if (default_data) {
         xdg_data_dirs = FALLBACK_DATA_DIRS;
     }
 #endif
@@ -526,14 +547,14 @@
         }
     }
 
-    res = check_if_settings_path_exists(inst, xdg_config_dirs, "/" VULKAN_DIR "/loader_settings.d/" VK_LOADER_SETTINGS_FILENAME,
-                                        settings_file_path);
+    res = check_settings_directories(inst, xdg_config_dirs, "/" VULKAN_DIR "/loader_settings.d/" VK_LOADER_SETTINGS_FILENAME,
+                                        settings_file_path, default_config);
     if (res == VK_SUCCESS) {
         return res;
     }
 
-    res = check_if_settings_path_exists(inst, SYSCONFDIR, "/" VULKAN_DIR "/loader_settings.d/" VK_LOADER_SETTINGS_FILENAME,
-                                        settings_file_path);
+    res = check_settings_directories(inst, SYSCONFDIR, "/" VULKAN_DIR "/loader_settings.d/" VK_LOADER_SETTINGS_FILENAME,
+                                        settings_file_path, true);
     if (res == VK_SUCCESS) {
         return res;
     }
@@ -545,8 +566,8 @@
         return res;
     }
 #endif
-    res = check_if_settings_path_exists(inst, xdg_data_dirs, "/" VULKAN_DIR "/loader_settings.d/" VK_LOADER_SETTINGS_FILENAME,
-                                        settings_file_path);
+    res = check_settings_directories(inst, xdg_data_dirs, "/" VULKAN_DIR "/loader_settings.d/" VK_LOADER_SETTINGS_FILENAME,
+                                        settings_file_path, default_data);
     if (res == VK_SUCCESS) {
         return res;
     }
