$NetBSD$

Bound the shared library scan and keep dedicated LLDB plugin discovery recursive.

--- source/Core/PluginManager.cpp.orig
+++ source/Core/PluginManager.cpp
@@ -259,6 +259,10 @@
 
   if (ft == fs::file_type::directory_file ||
       ft == fs::file_type::symlink_file || ft == fs::file_type::type_unknown) {
+    PluginDir::LoadPolicy *policy = (PluginDir::LoadPolicy *)baton;
+    if (*policy == PluginDir::LoadOnlyWithLLDBPrefix)
+      return FileSystem::eEnumerateDirectoryResultNext;
+
     // Try and recurse into anything that a directory or symbolic link. We must
     // also do this for unknown as sometimes the directory enumeration might be
     // enumerating a file system that doesn't have correct file type
@@ -280,8 +284,14 @@
   // meant exclusively for LLDB, the shared library directory is likely to
   // contain unrelated shared libraries that we do not want to load. Therefore,
   // limit the scan to libraries that start with g_plugin_prefix.
-  const std::array<PluginDir, 3> plugin_dirs = {
+  FileSpec local_plugin_dir = HostInfo::GetShlibDir();
+  if (local_plugin_dir) {
+    local_plugin_dir.AppendPathComponent("lldb");
+    local_plugin_dir.AppendPathComponent("plugins");
+  }
+  const std::array<PluginDir, 4> plugin_dirs = {
       PluginDir(HostInfo::GetShlibDir(), PluginDir::LoadOnlyWithLLDBPrefix),
+      PluginDir(local_plugin_dir, PluginDir::LoadAnyDylib),
       PluginDir(HostInfo::GetSystemPluginDir(), PluginDir::LoadAnyDylib),
       PluginDir(HostInfo::GetUserPluginDir(), PluginDir::LoadAnyDylib)};
 
