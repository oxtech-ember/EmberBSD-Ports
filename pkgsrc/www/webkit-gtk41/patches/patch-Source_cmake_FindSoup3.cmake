$NetBSD$

Use character classes for literal parentheses in CMake quoted regular
expressions when reading the installed libsoup version header.
Origin: EmberBSD contributors (AI-assisted).

--- Source/cmake/FindSoup3.cmake.orig
+++ Source/cmake/FindSoup3.cmake
@@ -67,13 +67,13 @@
 if (Soup3_INCLUDE_DIR AND NOT Soup3_VERSION AND EXISTS "${Soup3_INCLUDE_DIR}/libsoup/soup-version.h")
     file(READ "${Soup3_INCLUDE_DIR}/libsoup/soup-version.h" Soup3_VERSION_CONTENT)
 
-    string(REGEX MATCH "#define[\t ]+SOUP_MAJOR_VERSION[\t ]+\(([0-9]+)\)" _dummy "${Soup3_VERSION_CONTENT}")
+    string(REGEX MATCH "#define[\t ]+SOUP_MAJOR_VERSION[\t ]+[(]([0-9]+)[)]" _dummy "${Soup3_VERSION_CONTENT}")
     set(Soup3_VERSION_MAJOR "${CMAKE_MATCH_1}")
 
-    string(REGEX MATCH "#define[\t ]+SOUP_MINOR_VERSION[\t ]+\(([0-9]+)\)" _dummy "${Soup3_VERSION_CONTENT}")
+    string(REGEX MATCH "#define[\t ]+SOUP_MINOR_VERSION[\t ]+[(]([0-9]+)[)]" _dummy "${Soup3_VERSION_CONTENT}")
     set(Soup3_VERSION_MINOR "${CMAKE_MATCH_1}")
 
-    string(REGEX MATCH "#define[\t ]+SOUP_MICRO_VERSION[\t ]+\(([0-9]+)\)" _dummy "${Soup3_VERSION_CONTENT}")
+    string(REGEX MATCH "#define[\t ]+SOUP_MICRO_VERSION[\t ]+[(]([0-9]+)[)]" _dummy "${Soup3_VERSION_CONTENT}")
     set(Soup3_VERSION_MICRO "${CMAKE_MATCH_1}")
 
     set(Soup3_VERSION "${Soup3_VERSION_MAJOR}.${Soup3_VERSION_MINOR}.${Soup3_VERSION_MICRO}")
