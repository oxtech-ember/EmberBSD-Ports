$NetBSD: patch-cmake_QtSyncQtHelpers.cmake,v 1.3 2025/06/30 15:18:49 adam Exp $

Origin: pkgsrc; AI-assisted EmberBSD refresh for Qt 6.12.0, not submitted upstream.

Preserve the pkgsrc syncqt build ordering with the new generated-doc headers.

--- cmake/QtSyncQtHelpers.cmake.orig
+++ cmake/QtSyncQtHelpers.cmake
@@ -293,6 +293,7 @@
             ${module_headers_generated_for_docs}
             ${syncqt_all_args_rsp}
             ${QT_CMAKE_EXPORT_NAMESPACE}::syncqt
+            $<$<STREQUAL:${PROJECT_NAME},QtBase>:syncqt_build>
         VERBATIM
     )
 
