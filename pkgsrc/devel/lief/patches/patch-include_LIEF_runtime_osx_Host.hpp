$NetBSD$

Avoid NetBSD major/minor function macros in member initialization.

--- include/LIEF/runtime/osx/Host.hpp
+++ include/LIEF/runtime/osx/Host.hpp
@@ -32,8 +32,8 @@
     uint32_t patch = 0;
 
     version_t(uint32_t major, uint32_t minor, uint32_t patch) :
-      major(major),
-      minor(minor),
+      major{major},
+      minor{minor},
       patch(patch) {}
 
     bool operator<=(const version_t& rhs) const;
