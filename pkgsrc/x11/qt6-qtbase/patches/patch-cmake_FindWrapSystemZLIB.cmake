$NetBSD$

Honor an explicitly selected zlib installation on Darwin. Keep upstream's
SDK-switchable system-library behavior when no root has been selected.

--- cmake/FindWrapSystemZLIB.cmake.orig
+++ cmake/FindWrapSystemZLIB.cmake
@@ -15,7 +15,7 @@
     set(WrapSystemZLIB_FOUND ON)
 
     add_library(WrapSystemZLIB::WrapSystemZLIB INTERFACE IMPORTED)
-    if(APPLE)
+    if(APPLE AND NOT ZLIB_ROOT AND "$ENV{ZLIB_ROOT}" STREQUAL "")
         # On Darwin platforms FindZLIB sets IMPORTED_LOCATION to the absolute path of the library
         # within the framework. This ends up as an absolute path link flag, which we don't want,
         # because that makes our .prl files un-relocatable and also breaks iOS simulator_and_device
