$NetBSD$

Origin: EmberBSD (AI-assisted). Keep external package dependencies explicit.
Default upstream discovery remains unchanged. The common recipe opts in.
Upstream BSD-3-Clause license and copyright remain unchanged. Not submitted upstream.

--- cmake/OpenEXRSetup.cmake.orig
+++ cmake/OpenEXRSetup.cmake
@@ -212,6 +212,9 @@
 endif()
 set (ILMTHREAD_USE_TBB ${OPENEXR_USE_TBB})
 
+option(OPENEXR_REQUIRE_SYSTEM_LIBS
+  "Require installed codec libraries and Imath; reject bundled/download fallbacks" OFF)
+
 option(OPENEXR_FORCE_INTERNAL_DEFLATE "Force using an internal libdeflate" OFF)
 set (OPENEXR_USE_INTERNAL_DEFLATE OFF)
 
@@ -253,6 +256,9 @@
   set(deflate_VERSION_MAJOR "${CMAKE_MATCH_1}")
   set(deflate_VERSION_MINOR "${CMAKE_MATCH_2}")
 else()
+  if(OPENEXR_REQUIRE_SYSTEM_LIBS)
+    message(FATAL_ERROR "An installed libdeflate provider is required")
+  endif()
   # Using internal deflate
   if(OPENEXR_FORCE_INTERNAL_DEFLATE)
     message(STATUS "libdeflate forced internal, using vendored code")
@@ -371,6 +377,9 @@
   # For OpenEXR.pc.in for static build
   set(EXR_OPENJPH_PKGCONFIG_REQUIRES "openjph >= ${OPENEXR_MINIMUM_OPENJPH_VERSION}")
 else()
+  if(OPENEXR_REQUIRE_SYSTEM_LIBS)
+    message(FATAL_ERROR "An installed OpenJPH >= ${OPENEXR_MINIMUM_OPENJPH_VERSION} provider is required")
+  endif()
   # Using internal openjph
   set(OPENEXR_USE_INTERNAL_OPENJPH 1 CACHE INTERNAL
       "Whether OpenEXR bundles vendored OpenJPH into OpenEXRCore (0 or 1)" FORCE)
@@ -422,6 +431,9 @@
 endif()
 
 if(NOT TARGET Imath::Imath AND NOT Imath_FOUND)
+  if(OPENEXR_REQUIRE_SYSTEM_LIBS)
+    message(FATAL_ERROR "An installed Imath >= 3.1 provider is required")
+  endif()
   if(OPENEXR_FORCE_INTERNAL_IMATH)
     message(STATUS "Imath forced internal, fetching from ${OPENEXR_IMATH_REPO} @ ${OPENEXR_IMATH_TAG}")
   else()
@@ -526,6 +538,9 @@
   # For OpenEXR.pc.in for static build
   set(EXR_ZSTD_PKGCONFIG_REQUIRES "libzstd >= ${EXR_ZSTD_VERSION}")
 else()
+  if(OPENEXR_REQUIRE_SYSTEM_LIBS)
+    message(FATAL_ERROR "An installed zstd provider is required")
+  endif()
   # Using internal zstd
   set(zstd_version "${CMAKE_CURRENT_SOURCE_DIR}/external/zstd/lib/zstd.h")
   if(EXISTS "${zstd_version}")
