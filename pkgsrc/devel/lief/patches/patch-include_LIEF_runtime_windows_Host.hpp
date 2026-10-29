$NetBSD$

Avoid NetBSD major/minor function macros in member initialization.

--- include/LIEF/runtime/windows/Host.hpp
+++ include/LIEF/runtime/windows/Host.hpp
@@ -35,8 +35,8 @@
     version_t() = default;
 
     version_t(uint32_t major, uint32_t minor, uint32_t build_number) :
-      major(major),
-      minor(minor),
+      major{major},
+      minor{minor},
       build_number(build_number) {}
 
     bool operator<=(const version_t& rhs) const;
