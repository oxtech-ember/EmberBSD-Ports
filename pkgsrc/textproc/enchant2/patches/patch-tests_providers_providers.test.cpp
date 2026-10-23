$NetBSD$

Compare the provider prefix without its terminating NUL. The old comparison
skips real provider names and makes no-argument provider tests vacuous.
AI-assisted EmberBSD adaptation; not submitted upstream.

--- tests/providers/providers.test.cpp.orig
+++ tests/providers/providers.test.cpp
@@ -113,7 +113,7 @@
 #define PROVIDER_PREFIX "enchant_"
             size_t entry_len = strlen (dir_entry);
             if ((entry_len > g_module_suffix_len) &&
-                !strncmp(dir_entry, PROVIDER_PREFIX, sizeof(PROVIDER_PREFIX)) &&
+                !strncmp(dir_entry, PROVIDER_PREFIX, sizeof(PROVIDER_PREFIX) - 1) &&
                 !strcmp(dir_entry + (entry_len - g_module_suffix_len), G_MODULE_SUFFIX))
                 {
                     char *filename = g_build_filename (dir_name, dir_entry, NULL);
