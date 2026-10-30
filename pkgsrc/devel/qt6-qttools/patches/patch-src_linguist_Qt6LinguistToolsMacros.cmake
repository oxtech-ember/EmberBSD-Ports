$NetBSD$

Use the standard Qt tool wrapper for legacy translation commands too.

--- src/linguist/Qt6LinguistToolsMacros.cmake.orig
+++ src/linguist/Qt6LinguistToolsMacros.cmake
@@ -115,8 +115,14 @@
             set(qm_dep "${_abs_FILE}")
         endif()
 
+        _qt_internal_get_tool_wrapper_script_path(tool_wrapper)
+        if(tool_wrapper)
+            set(_lrelease_command "${tool_wrapper}" $<TARGET_FILE:${QT_CMAKE_EXPORT_NAMESPACE}::lrelease>)
+        else()
+            set(_lrelease_command ${QT_CMAKE_EXPORT_NAMESPACE}::lrelease)
+        endif()
         add_custom_command(OUTPUT ${qm}
-            COMMAND ${QT_CMAKE_EXPORT_NAMESPACE}::lrelease
+            COMMAND ${_lrelease_command}
             ARGS ${_LRELEASE_OPTIONS} ${_abs_FILE} -qm ${qm}
             DEPENDS ${qm_dep} VERBATIM
         )
