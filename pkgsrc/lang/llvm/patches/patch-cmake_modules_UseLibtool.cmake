# Origin: EmberBSD contributors (AI-assisted), not submitted upstream.
# Keep a supported selected ar/ranlib bootstrap without tool discovery.
--- cmake/modules/UseLibtool.cmake.orig
+++ cmake/modules/UseLibtool.cmake
@@ -1,3 +1,15 @@
+# Origin: EmberBSD contributors (AI-assisted), not submitted upstream.
+# Use the standard selected ar/ranlib rules for the initial tools only.
+set(LLVM_DARWIN_ARCHIVE_TOOL "libtool" CACHE STRING "Darwin static archive tool: libtool or ar")
+set_property(CACHE LLVM_DARWIN_ARCHIVE_TOOL PROPERTY STRINGS libtool ar)
+if(NOT LLVM_DARWIN_ARCHIVE_TOOL STREQUAL "libtool" AND
+   NOT LLVM_DARWIN_ARCHIVE_TOOL STREQUAL "ar")
+  message(FATAL_ERROR "LLVM_DARWIN_ARCHIVE_TOOL must be libtool or ar")
+endif()
+if(LLVM_DARWIN_ARCHIVE_TOOL STREQUAL "ar")
+  return()
+endif()
+
 # if CMAKE_LIBTOOL is not set, try and find it with xcrun or find_program
 if(NOT CMAKE_LIBTOOL)
   if(NOT CMAKE_XCRUN)
