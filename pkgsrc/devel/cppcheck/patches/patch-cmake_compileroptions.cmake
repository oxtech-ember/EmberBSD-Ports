$NetBSD$

Keep the selected libstdc++ debug ABI with common providers.
Origin: EmberBSD contributors (AI-assisted), not submitted upstream.

--- cmake/compileroptions.cmake.orig
+++ cmake/compileroptions.cmake
@@ -260,7 +260,8 @@
 # TODO: check if this can be enabled again - also done in Makefile
 if(CMAKE_SYSTEM_NAME STREQUAL "Linux" AND
-    CMAKE_CXX_COMPILER_ID MATCHES "Clang")
+    CMAKE_CXX_COMPILER_ID MATCHES "Clang" AND
+    NOT CPPCHK_GLIBCXX_DEBUG)
 
     add_compile_options(-U_GLIBCXX_DEBUG)
 endif()
