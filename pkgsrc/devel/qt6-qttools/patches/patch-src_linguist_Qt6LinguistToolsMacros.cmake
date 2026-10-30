$NetBSD$

Use the standard Qt tool wrapper for legacy translation commands too.

--- src/linguist/Qt6LinguistToolsMacros.cmake.orig
+++ src/linguist/Qt6LinguistToolsMacros.cmake
@@ -115,8 +115,10 @@
             set(qm_dep "${_abs_FILE}")
         endif()
 
+        _qt_internal_get_tool_wrapper_script_path(tool_wrapper)
         add_custom_command(OUTPUT ${qm}
-            COMMAND ${QT_CMAKE_EXPORT_NAMESPACE}::lrelease
+            COMMAND "${tool_wrapper}"
+                    $<TARGET_FILE:${QT_CMAKE_EXPORT_NAMESPACE}::lrelease>
             ARGS ${_LRELEASE_OPTIONS} ${_abs_FILE} -qm ${qm}
             DEPENDS ${qm_dep} VERBATIM
         )
