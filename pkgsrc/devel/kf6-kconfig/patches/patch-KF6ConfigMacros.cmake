$NetBSD$

Run the native KConfig generator through Qt's selected tool wrapper.

--- KF6ConfigMacros.cmake.orig
+++ KF6ConfigMacros.cmake
@@ -131,8 +131,14 @@ function(KCONFIG_ADD_KCFG_FILES _sources)
         endif()
 
         # the command for creating the source file from the kcfg file
+        _qt_internal_get_tool_wrapper_script_path(tool_wrapper)
+        if(tool_wrapper)
+            set(_kconfig_command "${tool_wrapper}" $<TARGET_FILE:KF6::kconfig_compiler>)
+        else()
+            set(_kconfig_command KF6::kconfig_compiler)
+        endif()
         add_custom_command(OUTPUT ${_header_FILE} ${_src_FILE}
-                          COMMAND KF6::kconfig_compiler
+                          COMMAND ${_kconfig_command}
                           ARGS ${_kcfg_FILE} ${_tmp_FILE} -d ${CMAKE_CURRENT_BINARY_DIR}/${_rel_PATH}
                           MAIN_DEPENDENCY ${_tmp_FILE}
                           DEPENDS ${_kcfg_FILE} KF6::kconfig_compiler)
