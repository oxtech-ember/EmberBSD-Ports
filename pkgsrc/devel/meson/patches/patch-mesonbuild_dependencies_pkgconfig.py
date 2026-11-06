$NetBSD$

Clear inherited target pkg-config sysroot for build-machine queries.

--- mesonbuild/dependencies/pkgconfig.py.orig
+++ mesonbuild/dependencies/pkgconfig.py
@@ -280,6 +280,10 @@
         sysroot = self.env.properties[self.for_machine].get_sys_root()
         if sysroot:
             env.set('PKG_CONFIG_SYSROOT_DIR', [sysroot])
+        elif self.env.is_cross_build() and self.for_machine == MachineChoice.BUILD:
+            # The Meson process may inherit the target cross-build sysroot.
+            # Build-machine pkg-config must resolve host tools and metadata.
+            env.set('PKG_CONFIG_SYSROOT_DIR', [''])
         pkg_config_libdir_prop = self.env.properties[self.for_machine].get_pkg_config_libdir()
         if pkg_config_libdir_prop:
             env.set('PKG_CONFIG_LIBDIR', pkg_config_libdir_prop)
