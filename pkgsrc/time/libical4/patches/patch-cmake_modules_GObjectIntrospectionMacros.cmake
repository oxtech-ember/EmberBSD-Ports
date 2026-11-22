$NetBSD$

Origin: EmberBSD contributors (AI-assisted).
Build each GIR once before compiling its typelib with parallel Make.

--- cmake/modules/GObjectIntrospectionMacros.cmake.orig
+++ cmake/modules/GObjectIntrospectionMacros.cmake
@@ -147,4 +147,5 @@
       ${_gir_typelibs}
     COMMENT "Target for the gobject introspection typelibs"
   )
+  add_dependencies(gir-typelibs-${_gir_name} gir-girs-${_gir_name})
 endmacro(gir_add_introspections)
