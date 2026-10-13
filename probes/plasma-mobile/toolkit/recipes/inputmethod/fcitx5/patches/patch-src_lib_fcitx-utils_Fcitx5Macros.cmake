$NetBSD$

Keep exported include paths relative to the installed package prefix.

Origin: EmberBSD (AI-assisted). Not submitted upstream.

--- src/lib/fcitx-utils/Fcitx5Macros.cmake.orig
+++ src/lib/fcitx-utils/Fcitx5Macros.cmake
@@ -11,7 +11,7 @@
     set(FCITX_ADDON_TYPE "StaticLibrary")
 endif()
 
-include(WriteBasicConfigVersionFile)
+include(CMakePackageConfigHelpers)
 
 function(fcitx5_import_addons target)
   set(options)
@@ -120,12 +120,16 @@
     add_library(${FEM_TARGET}-interface INTERFACE)
     add_library(Fcitx5::Module::${EXPORTNAME} ALIAS ${FEM_TARGET}-interface)
     set_target_properties(${FEM_TARGET}-interface PROPERTIES INTERFACE_INCLUDE_DIRECTORIES "${FEM_BUILD_INCLUDE_DIRECTORIES}")
-    configure_file(
+    configure_package_config_file(
         "${_Fcitx5Macro_SELF_DIR}/Fcitx5ModuleTemplate.cmake.in"
-        "${CMAKE_CURRENT_BINARY_DIR}/Fcitx5Module${EXPORTNAME}.cmake" @ONLY)
-    configure_file(
+        "${CMAKE_CURRENT_BINARY_DIR}/Fcitx5Module${EXPORTNAME}.cmake"
+        INSTALL_DESTINATION "${FEM_LIB_INSTALL_DIR}/cmake/Fcitx5Module${EXPORTNAME}"
+        PATH_VARS _MODULE_HEADER_DIR)
+    configure_package_config_file(
         "${_Fcitx5Macro_SELF_DIR}/Fcitx5ModuleTemplate.cmake.in"
-        "${CMAKE_CURRENT_BINARY_DIR}/Fcitx5Module${EXPORTNAME}Config.cmake" @ONLY)
+        "${CMAKE_CURRENT_BINARY_DIR}/Fcitx5Module${EXPORTNAME}Config.cmake"
+        INSTALL_DESTINATION "${FEM_LIB_INSTALL_DIR}/cmake/Fcitx5Module${EXPORTNAME}"
+        PATH_VARS _MODULE_HEADER_DIR)
 
     if (NOT FEM_VERSION)
         set(FEM_VERSION ${PROJECT_VERSION})
