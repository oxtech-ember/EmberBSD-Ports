$NetBSD$

Origin: EmberBSD contributors (AI-assisted), not submitted upstream.
Avoid Apple SDK autodetection for an explicitly non-Apple target.

--- cmake/QtAutoDetectHelpers.cmake.orig
+++ cmake/QtAutoDetectHelpers.cmake
@@ -342,6 +342,16 @@
         return()
     endif()
 
+    # Before project(), APPLE can describe the build host instead of the target.
+    # Keep native Darwin and Qt's Apple targets, but skip Apple SDK autodetection
+    # when an explicit non-Apple target system was selected.
+    if(CMAKE_SYSTEM_NAME)
+        set(_qt_apple_target_systems Darwin iOS tvOS watchOS visionOS)
+        if(NOT CMAKE_SYSTEM_NAME IN_LIST _qt_apple_target_systems)
+            return()
+        endif()
+    endif()
+
     if("${QT_QMAKE_TARGET_MKSPEC}" STREQUAL "macx-ios-clang")
         set(CMAKE_SYSTEM_NAME "iOS" CACHE STRING "")
     elseif("${QT_QMAKE_TARGET_MKSPEC}" STREQUAL "macx-visionos-clang")
