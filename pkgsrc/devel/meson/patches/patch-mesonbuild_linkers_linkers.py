$NetBSD: patch-mesonbuild_linkers_linkers.py,v 1.3 2026/08/11 11:43:05 wiz Exp $

Retain the conditional SunOS thin-archive restriction. Restore upstream rpath-link policy.
Origin: pkgsrc adaptation by EmberBSD, AI-assisted.

--- mesonbuild/linkers/linkers.py.orig
+++ mesonbuild/linkers/linkers.py
@@ -404,7 +404,7 @@
         thinargs = ''
         if '[D]' in stdo:
             stdargs += 'D'
-        if '[T]' in stdo:
+        if '[T]' in stdo and not mesonlib.is_sunos():
             thinargs = 'T'
         self.std_args = [stdargs]
         self.std_thin_args = [stdargs + thinargs]
