$NetBSD$

Route cross introspection through real target queries and ELF inspection.
Keep scanner diagnostics, target metadata and installed typelib generation.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- Source/cmake/FindGI.cmake.orig
+++ Source/cmake/FindGI.cmake
@@ -55,7 +55,22 @@
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
+    if (NOT IS_ABSOLUTE "${GI_TARGET_GIR_DIR}" OR NOT IS_DIRECTORY "${GI_TARGET_GIR_DIR}")
+        message(FATAL_ERROR "Cross introspection requires an absolute target GI_TARGET_GIR_DIR directory")
+    endif ()
+endif ()
+
 find_package(PkgConfig QUIET)
+
 
 if (PKG_CONFIG_FOUND)
     if (PACKAGE_FIND_VERSION_COUNT GREATER 0)
@@ -249,6 +264,12 @@
     set(typ_path "${CMAKE_BINARY_DIR}/${gir_name}.typelib")
 
     set(scanner_flags)
+    set(compiler_flags)
+    if (CMAKE_CROSSCOMPILING)
+        list(APPEND scanner_flags "--use-ldd-wrapper=${GI_LDD_WRAPPER}"
+            "--add-include-path=${GI_TARGET_GIR_DIR}")
+        list(APPEND compiler_flags "--includedir=${GI_TARGET_GIR_DIR}")
+    endif ()
     if (GI_HAVE_SOURCES_TOP_DIRS)
         list(APPEND scanner_flags "--sources-top-dirs=${CMAKE_SOURCE_DIR}")
     endif ()
@@ -380,6 +401,7 @@
         VERBATIM
         COMMAND "${GI_COMPILER_EXE}"
             "--includedir=${CMAKE_BINARY_DIR}"
+            ${compiler_flags}
             "--output=${typ_path}"
             "${gir_path}"
     )
