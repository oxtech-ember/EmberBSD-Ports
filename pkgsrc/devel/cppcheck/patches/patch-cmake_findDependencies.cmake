$NetBSD$

Keep Cppcheck capabilities with shared current dependencies.
Origin: EmberBSD contributors (AI-assisted), not submitted upstream.

--- cmake/findDependencies.cmake.orig
+++ cmake/findDependencies.cmake
@@ -29,11 +29,10 @@
 endif()
 
 if(HAVE_RULES)
-    find_path(PCRE_INCLUDE pcre.h)
-    find_library(PCRE_LIBRARY NAMES pcre pcred)
-    if(NOT PCRE_LIBRARY OR NOT PCRE_INCLUDE)
-        message(FATAL_ERROR "pcre dependency for RULES has not been found")
-    endif()
+    find_package(PkgConfig REQUIRED)
+    pkg_check_modules(PCRE2 REQUIRED IMPORTED_TARGET libpcre2-8>=10.47)
+    set(PCRE_LIBRARY PkgConfig::PCRE2)
+    set(PCRE_INCLUDE "${PCRE2_INCLUDE_DIRS}")
 else()
     set(PCRE_LIBRARY "")
 endif()
@@ -97,10 +96,17 @@
         set(Boost_FOUND ON)
         set(Boost_INCLUDE_DIRS "${BOOST_INCLUDEDIR}")
         set(Boost_VERSION_STRING "")  # TODO: set proper value
-    elseif(USE_BOOST STREQUAL "Auto")
-        find_package(Boost)
     else()
-        find_package(Boost REQUIRED)
+        if(USE_BOOST STREQUAL "Auto")
+            find_package(boost_headers CONFIG)
+        else()
+            find_package(boost_headers CONFIG REQUIRED)
+        endif()
+        set(Boost_FOUND "${boost_headers_FOUND}")
+        if(Boost_FOUND)
+            get_target_property(Boost_INCLUDE_DIRS Boost::headers INTERFACE_INCLUDE_DIRECTORIES)
+            set(Boost_VERSION_STRING "${boost_headers_VERSION}")
+        endif()
     endif()
 endif()
 
