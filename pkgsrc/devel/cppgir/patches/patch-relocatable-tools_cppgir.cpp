$NetBSD$

Resolve installed data relative to the actual executable after prefix relocation.
Explicit search inputs and absolute installation directories retain their meaning.

--- tools/cppgir.cpp.orig
+++ tools/cppgir.cpp
@@ -6,6 +6,12 @@
 
 #include <boost/algorithm/string/classification.hpp>
 #include <boost/algorithm/string/split.hpp>
+#define BOOST_DLL_USE_STD_FS
+#include <boost/dll/runtime_symbol_info.hpp>
+
+#if !defined(_WIN32) || defined(__CYGWIN__)
+#include <unistd.h>
+#endif
 
 #include <map>
 #include <set>
@@ -32,6 +38,46 @@
 static const char *PATH_ARR_SEP = ":";
 #endif
 static const std::string GIR_SUBDIR{"gir-1.0"};
+
+// Prefer the OS-reported executable location. The POSIX fallback also works
+// on systems where the optional procfs used by Boost.DLL is not mounted.
+static fs::path
+executable_directory(const char *arg0)
+{
+  fs::error_code ec;
+  auto executable = boost::dll::program_location(ec);
+  if (!ec && !executable.empty()) {
+    auto resolved = fs::canonical(executable, ec);
+    if (!ec)
+      return resolved.parent_path();
+  }
+#if !defined(_WIN32) || defined(__CYGWIN__)
+  const fs::path name{arg0 ? arg0 : ""};
+  if (name.empty())
+    return {};
+  if (name.has_parent_path()) {
+    auto resolved = fs::canonical(name, ec);
+    if (!ec)
+      return resolved.parent_path();
+    return {};
+  }
+  const char *envpath = getenv("PATH");
+  if (envpath) {
+    std::vector<std::string> dirs;
+    boost::split(dirs, envpath, boost::is_any_of(":"));
+    for (const auto &dir : dirs) {
+      const auto candidate = fs::path(dir) / name;
+      if (access(candidate.c_str(), X_OK) != 0 ||
+          !fs::is_regular_file(candidate, ec))
+        continue;
+      auto resolved = fs::canonical(candidate, ec);
+      if (!ec)
+        return resolved.parent_path();
+    }
+  }
+#endif
+  return {};
+}
 
 Log _loglevel = Log::WARNING;
 
@@ -389,6 +435,15 @@
     return 0;
   }
 
+  const auto executable_dir = executable_directory(argv[0]);
+  if (executable_dir.empty())
+    return die(helpdesc, "cannot locate generator executable for installed data");
+  const auto installed_path = [&](const std::string &value) {
+    const fs::path path{value};
+    return path.is_absolute() ? path.string()
+                             : (executable_dir / path).lexically_normal().string();
+  };
+
   // collect some more files
   addsplit(ignore_files, fpath_ignore);
   addsplit(suppress_files, fpath_suppress);
@@ -438,7 +493,7 @@
     girdirs.push_back(GI_STRINGIFY(GI_GIR_DIR));
   #endif
   #ifdef GI_DATA_DIR
-    girdirs.push_back(GI_STRINGIFY(GI_DATA_DIR));
+    girdirs.push_back(installed_path(GI_STRINGIFY(GI_DATA_DIR)));
   #endif
   #ifdef DEFAULT_GIRPATH
     // optional (hard) fallback
@@ -450,8 +505,12 @@
     logger(Log::DEBUG, "extending GIR path " + d);
 
   // system default
-  if (!GI_DEFAULT_IGNORE.empty())
-    addsplit(ignore_files, GI_DEFAULT_IGNORE);
+  if (!GI_DEFAULT_IGNORE.empty()) {
+    std::vector<std::string> defaults;
+    addsplit(defaults, GI_DEFAULT_IGNORE);
+    for (const auto &path : defaults)
+      ignore_files.push_back(installed_path(path));
+  }
 
   // collect girs to process
   addsplit(girs, gir_top);
