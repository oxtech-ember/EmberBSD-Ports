$NetBSD$

Allow the C-only software renderer without a target C++ SDK.

--- env_support/cmake/main.cmake.orig
+++ env_support/cmake/main.cmake
@@ -122,6 +122,9 @@
 file(GLOB_RECURSE SOURCES ${LVGL_ROOT_DIR}/src/*.c
                           ${LVGL_ROOT_DIR}/src/*.cpp
                           ${LVGL_ROOT_DIR}/src/*.S)
+if(LV_BUILD_C_ONLY)
+    list(FILTER SOURCES EXCLUDE REGEX "\\.cpp$")
+endif()
 file(GLOB_RECURSE EXAMPLE_SOURCES ${LVGL_ROOT_DIR}/examples/*.c)
 file(GLOB_RECURSE DEMO_SOURCES ${LVGL_ROOT_DIR}/demos/*.c)
 file(GLOB_RECURSE THORVG_SOURCES ${LVGL_ROOT_DIR}/src/libs/thorvg/*.cpp
