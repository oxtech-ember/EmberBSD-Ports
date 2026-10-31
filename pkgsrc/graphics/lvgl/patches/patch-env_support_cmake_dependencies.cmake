$NetBSD$

Allow integer-only configurations on C foundations without libm.

--- env_support/cmake/dependencies.cmake.orig
+++ env_support/cmake/dependencies.cmake
@@ -15,7 +15,8 @@
       "Install `pkg-config` to improve dependency detection.")
 endif()
 
-if(UNIX)
+option(LV_BUILD_USE_LIBM "Link the system math library" ON)
+if(UNIX AND LV_BUILD_USE_LIBM)
   lvgl_link_system_lib(TARGETS m PKG_LIB_PRIVATE -lm)
 endif()
 
