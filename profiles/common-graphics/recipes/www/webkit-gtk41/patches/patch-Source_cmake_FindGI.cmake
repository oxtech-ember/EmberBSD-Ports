$NetBSD$

Route cross introspection through real target queries and ELF inspection.
Keep scanner diagnostics, target metadata and installed typelib generation.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- Source/cmake/FindGI.cmake.orig
+++ Source/cmake/FindGI.cmake
@@ -55,8 +55,20 @@
     return()
 endif ()
 
+# Native scanner/compiler programs inspect target libraries. The launcher runs
+# the real target dumper; the ldd wrapper only reads its ELF dependency names.
+if (CMAKE_CROSSCOMPILING)
+    if (NOT IS_ABSOLUTE "${GI_LDD_WRAPPER}" OR NOT EXISTS "${GI_LDD_WRAPPER}")
+        message(FATAL_ERROR "Cross introspection requires an absolute GI_LDD_WRAPPER")
+    endif ()
+    if ("$ENV{GI_CROSS_LAUNCHER}" STREQUAL "")
+        message(FATAL_ERROR "Cross introspection requires a real GI_CROSS_LAUNCHER")
+    endif ()
+endif ()
+
 find_package(PkgConfig QUIET)
 
+
 if (PKG_CONFIG_FOUND)
     if (PACKAGE_FIND_VERSION_COUNT GREATER 0)
         set(_gi_version_cmp ">=${PACKAGE_FIND_VERSION}")
@@ -249,6 +261,9 @@
     set(typ_path "${CMAKE_BINARY_DIR}/${gir_name}.typelib")
 
     set(scanner_flags)
+    if (CMAKE_CROSSCOMPILING)
+        list(APPEND scanner_flags "--use-ldd-wrapper=${GI_LDD_WRAPPER}")
+    endif ()
     if (GI_HAVE_SOURCES_TOP_DIRS)
         list(APPEND scanner_flags "--sources-top-dirs=${CMAKE_SOURCE_DIR}")
     endif ()
