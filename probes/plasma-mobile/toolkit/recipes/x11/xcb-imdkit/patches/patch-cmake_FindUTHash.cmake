$NetBSD$

Require the selected system uthash and use its discovered include directory.
Do not silently fall back to the bundled uthash 1.8.

--- cmake/FindUTHash.cmake.orig
+++ cmake/FindUTHash.cmake
@@ -13,6 +13,6 @@
 if(UTHash_FOUND AND NOT TARGET UTHash::UTHash)
     add_library(UTHash::UTHash INTERFACE IMPORTED )
     set_target_properties(UTHash::UTHash PROPERTIES
-        INTERFACE_INCLUDE_DIRECTORIES "${EXECINFO_INCLUDE_DIR}"
+        INTERFACE_INCLUDE_DIRECTORIES "${UTHash_INCLUDE_DIR}"
     )
 endif()
