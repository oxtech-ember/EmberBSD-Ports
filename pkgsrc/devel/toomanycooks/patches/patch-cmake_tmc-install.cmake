# $NetBSD$

Install a correct package version and preserve BSD platform and license paths.

--- cmake/tmc-install.cmake.orig
+++ cmake/tmc-install.cmake
@@ -19,7 +19,7 @@
 )
 
 install(FILES LICENSE
-  DESTINATION licenses
+  DESTINATION ${CMAKE_INSTALL_DATADIR}/licenses/toomanycooks
   COMPONENT TooManyCooks_Development
 )
 
