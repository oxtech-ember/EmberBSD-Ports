Require Python 3 only when compiling translation maps.

Origin: EmberBSD (AI-assisted).

--- cmake/build-tsfiles.cmake.orig
+++ cmake/build-tsfiles.cmake
@@ -47,9 +47,13 @@
         continue()
     endif()
 
+    if(NOT Python3_EXECUTABLE OR Python3_EXECUTABLE MATCHES "-NOTFOUND$")
+        message(FATAL_ERROR "Python 3 is required to compile KI18n .pmap files")
+    endif()
+
     message(STATUS "building... ${pmap_file} to ${pmapc_file}" )
     list(APPEND commands
-        COMMAND ${Python3_EXECUTABLE}
+        COMMAND "${Python3_EXECUTABLE}"
             -B
             ${_ki18n_pmap_compile_script}
             ${PO_DIR}/${pmap_file}
