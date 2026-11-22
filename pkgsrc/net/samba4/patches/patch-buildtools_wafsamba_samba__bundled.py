$NetBSD$

Origin: EmberBSD (AI-assisted).
Upstream status: not submitted.

Check the target TDB and tevent bindings without importing foreign extensions
into the Python interpreter running Waf. The target libraries and their
Python extensions share the same upstream PACKAGE_VERSION.

--- buildtools/wafsamba/samba_bundled.py.orig
+++ buildtools/wafsamba/samba_bundled.py
@@ -1,5 +1,6 @@
 # functions to support bundled libraries
 
+import os
 import sys
 from waflib import Build, Options, Logs
 from waflib.Configure import conf
@@ -255,17 +256,28 @@
     # versions
     minversion = minimum_library_version(conf, libname, minversion)
 
-    try:
-        m = __import__(modulename)
-    except ImportError:
-        found = False
+    target_site = os.environ.get('SAMBA_TARGET_PYTHON_SITE')
+    if conf.env.CROSS_COMPILE and target_site:
+        # Both bindings embed their native package's PACKAGE_VERSION. Check
+        # that package's target .pc file and the installed binding for this ABI.
+        modules = {'tdb': ('tdb.so',), 'tevent': ('tevent.py', '_tevent.so')}
+        files = modules.get(modulename)
+        found = (files is not None and
+                 all(os.path.isfile(os.path.join(target_site, f)) for f in files) and
+                 conf.CHECK_CFG(package=modulename, args='--atleast-version=' + minversion,
+                                msg='Checking target Python module %s >= %s' % (modulename, minversion)))
     else:
         try:
-            version = m.__version__
-        except AttributeError:
+            m = __import__(modulename)
+        except ImportError:
             found = False
         else:
-            found = tuplize_version(version) >= tuplize_version(minversion)
+            try:
+                version = m.__version__
+            except AttributeError:
+                found = False
+            else:
+                found = tuplize_version(version) >= tuplize_version(minversion)
     if not found and not conf.LIB_MAY_BE_BUNDLED(libname):
         Logs.error('ERROR: Python module %s of version %s not found, and bundling disabled' % (libname, minversion))
         sys.exit(1)
