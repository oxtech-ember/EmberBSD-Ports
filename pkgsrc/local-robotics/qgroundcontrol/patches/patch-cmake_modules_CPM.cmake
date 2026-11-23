$NetBSD$

Origin: EmberBSD (AI-assisted), local, not submitted upstream.
Report a package that find_package() found to the caller, so that
QGC_USE_SYSTEM_LIBS can use installed libraries.

--- cmake/modules/CPM.cmake.orig
+++ cmake/modules/CPM.cmake
@@ -803,6 +803,7 @@ function(CPMAddPackage)
       cpm_find_package(${CPM_ARGS_NAME} "${CPM_ARGS_VERSION}" ${CPM_ARGS_FIND_PACKAGE_ARGUMENTS})
 
       if(CPM_PACKAGE_FOUND)
+        set(${CPM_ARGS_NAME}_FOUND TRUE PARENT_SCOPE)
         cpm_export_variables(${CPM_ARGS_NAME})
         return()
       endif()
