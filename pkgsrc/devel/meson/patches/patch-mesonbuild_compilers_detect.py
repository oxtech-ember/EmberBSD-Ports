$NetBSD: patch-mesonbuild_compilers_detect.py,v 1.8 2025/10/09 16:55:17 ryoon Exp $

Select only the common Python 3.14 Cython entry point. Upstream already passes the language when preprocessing stdin.
Origin: pkgsrc adaptation by EmberBSD, AI-assisted.

--- mesonbuild/compilers/detect.py.orig
+++ mesonbuild/compilers/detect.py
@@ -73,7 +73,7 @@
 defaults['rust'] = ['rustc']
 defaults['swift'] = ['swiftc']
 defaults['vala'] = ['valac']
-defaults['cython'] = ['cython', 'cython3'] # Official name is cython, but Debian renamed it to cython3.
+defaults['cython'] = ['cython-3.14'] # EmberBSD's common Python version.
 defaults['static_linker'] = ['ar', 'gar']
 defaults['strip'] = ['strip']
 defaults['vs_static_linker'] = ['lib']
