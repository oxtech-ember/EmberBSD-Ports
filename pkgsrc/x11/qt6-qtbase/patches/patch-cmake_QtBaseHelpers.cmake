# Exclude generated preliminary specs from an in-source reconfigure install.
--- cmake/QtBaseHelpers.cmake.orig
+++ cmake/QtBaseHelpers.cmake
@@ -139,6 +139,7 @@
     file(GLOB mkspecs_subdirs
         LIST_DIRECTORIES TRUE
         "${PROJECT_SOURCE_DIR}/mkspecs/*")
+    list(REMOVE_ITEM mkspecs_subdirs "${PROJECT_SOURCE_DIR}/mkspecs/preliminary")
     foreach(entry IN LISTS mkspecs_subdirs)
         if(IS_DIRECTORY ${entry})
             qt_copy_or_install(DIRECTORY "${entry}"
