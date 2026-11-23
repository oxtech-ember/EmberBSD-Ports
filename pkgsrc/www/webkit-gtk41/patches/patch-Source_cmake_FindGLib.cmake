$NetBSD$

Close the header-content variable expansion when pkg-config leaves the GLib
version unset. This allows the target glibconfig.h to provide the version.
Origin: EmberBSD contributors (AI-assisted).

--- Source/cmake/FindGLib.cmake.orig
+++ Source/cmake/FindGLib.cmake
@@ -128,13 +128,13 @@
 if (NOT GLib_VERSION AND EXISTS "${GLib_Config_INCLUDE_DIR}/glibconfig.h")
     file(READ "${GLib_Config_INCLUDE_DIR}/glibconfig.h" GLib_Config_CONTENT)
 
-    string(REGEX MATCH "#define +GLIB_MAJOR_VERSION +([0-9]+)" _dummy "${GLib_Config_CONTENT")
+    string(REGEX MATCH "#define +GLIB_MAJOR_VERSION +([0-9]+)" _dummy "${GLib_Config_CONTENT}")
     set(GLib_VERSION_MAJOR "${CMAKE_MATCH_1}")
 
-    string(REGEX MATCH "#define +GLIB_MINOR_VERSION +([0-9]+)" _dummy "${GLib_Config_CONTENT")
+    string(REGEX MATCH "#define +GLIB_MINOR_VERSION +([0-9]+)" _dummy "${GLib_Config_CONTENT}")
     set(GLib_VERSION_MINOR "${CMAKE_MATCH_1}")
 
-    string(REGEX MATCH "#define +GLIB_MICRO_VERSION +([0-9]+)" _dummy "${GLib_Config_CONTENT")
+    string(REGEX MATCH "#define +GLIB_MICRO_VERSION +([0-9]+)" _dummy "${GLib_Config_CONTENT}")
     set(GLib_VERSION_MICRO "${CMAKE_MATCH_1}")
 
     set(GLib_VERSION "${GLib_VERSION_MAJOR}.${GLib_VERSION_MINOR}.${GLib_VERSION_MICRO}")
