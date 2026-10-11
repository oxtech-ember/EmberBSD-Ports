$NetBSD$

Origin: EmberBSD (AI-assisted). Resolve Wayland protocol data through the target
sysroot. pkg-config variables alone otherwise name the host installation.

--- find-modules/FindWaylandProtocols.cmake.orig
+++ find-modules/FindWaylandProtocols.cmake
@@ -24,7 +24,15 @@
 pkg_check_modules(PKG_wayland_protocols QUIET wayland-protocols)
 
 set(WaylandProtocols_VERSION ${PKG_wayland_protocols_VERSION})
-pkg_get_variable(WaylandProtocols_DATADIR wayland-protocols pkgdatadir)
+pkg_get_variable(_WaylandProtocols_pkgdatadir wayland-protocols pkgdatadir)
+
+# pkg-config data variables are not sysroot-prefixed. Resolve the actual data
+# through CMake so cross builds obey CMAKE_FIND_ROOT_PATH.
+find_path(WaylandProtocols_DATADIR
+    NAMES stable/xdg-shell/xdg-shell.xml
+    HINTS "${_WaylandProtocols_pkgdatadir}"
+    NO_DEFAULT_PATH
+)
 
 include(FindPackageHandleStandardArgs)
 find_package_handle_standard_args(WaylandProtocols
