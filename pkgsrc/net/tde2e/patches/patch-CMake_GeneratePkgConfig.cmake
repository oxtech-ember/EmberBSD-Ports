# $NetBSD$

Export portable dependencies for installed tde2e consumers.
Origin: EmberBSD.

--- CMake/GeneratePkgConfig.cmake.orig
+++ CMake/GeneratePkgConfig.cmake
@@ -71,7 +71,13 @@
   set(REQS "")
   set(LIBS "")
   foreach (LIB ${LIST})
-    if (TARGET "${LIB}")
+    if ("${LIB}" STREQUAL "OpenSSL::Crypto")
+      set(HAS_REQS 1)
+      list(APPEND REQS libcrypto)
+    elseif ("${LIB}" STREQUAL "ZLIB::ZLIB")
+      set(HAS_REQS 1)
+      list(APPEND REQS zlib)
+    elseif (TARGET "${LIB}")
       if ("${LIBRARY_TYPE}" STREQUAL "SHARED_LIBRARY")
         get_target_property(LIB_TYPE "${LIB}" TYPE)
         if ("${LIB_TYPE}" STREQUAL "STATIC_LIBRARY")
