$NetBSD$

Install a shared Flang-RT in a chosen library directory with a versioned
name, so a package can ship it as a normal runtime library. The defaults
keep the upstream resource directory layout.

--- flang-rt/cmake/modules/AddFlangRT.cmake.orig
+++ flang-rt/cmake/modules/AddFlangRT.cmake
@@ -396,9 +396,20 @@
           LIBRARY_OUTPUT_DIRECTORY "${RUNTIMES_OUTPUT_RESOURCE_LIB_DIR}"
         )
 
+      # A packaged shared runtime is a normal library: it is installed in
+      # the library directory, has a versioned name, and a program loads
+      # one copy for all of its Fortran libraries.
+      if (FLANG_RT_SHARED_SOVERSION AND tgtname STREQUAL name_shared)
+        set_target_properties(${tgtname} PROPERTIES
+          VERSION "${FLANG_RT_SHARED_SOVERSION}"
+          SOVERSION "${FLANG_RT_SHARED_SOVERSION}")
+      endif ()
+      if (NOT FLANG_RT_INSTALL_SHARED_LIB_PATH)
+        set(FLANG_RT_INSTALL_SHARED_LIB_PATH "${RUNTIMES_INSTALL_RESOURCE_LIB_PATH}")
+      endif ()
       install(TARGETS ${tgtname}
           ARCHIVE DESTINATION "${RUNTIMES_INSTALL_RESOURCE_LIB_PATH}"
-          LIBRARY DESTINATION "${RUNTIMES_INSTALL_RESOURCE_LIB_PATH}"
+          LIBRARY DESTINATION "${FLANG_RT_INSTALL_SHARED_LIB_PATH}"
         )
     endif ()
 
