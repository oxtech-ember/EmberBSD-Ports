$NetBSD$

Use the stable ABI suffix for Python built with the untagged EXT_SUFFIX
".so", as pkgsrc builds it. Without this, setuptools names py_limited_api
extensions "name.so" instead of "name.abi3.so".
Origin: EmberBSD (AI-assisted). Upstream status: not submitted.

--- setuptools/command/build_ext.py
+++ setuptools/command/build_ext.py
@@ -82,18 +82,25 @@
         return None
     if suffix.endswith('.pyd') and not suffix.startswith('_d'):
         return '.pyd'
-    if not suffix.startswith('.cpython-'):
-        return None
+    tag = suffix
+    if not tag.startswith('.cpython-'):
+        # pkgsrc builds CPython with the untagged EXT_SUFFIX ".so". Its
+        # loader still accepts the stable ABI suffix; SOABI has the tag.
+        soabi = get_config_var('SOABI')
+        if not isinstance(soabi, str) or not soabi.startswith('cpython-'):
+            return None
+        tag = '.' + soabi
     if get_config_var('DYNLOADFILE') == 'dynload_hpux.o':
         return None
 
     # The 3.13t and 3.14t loaders cannot import .abi3t files.
-    if suffix.startswith(('.cpython-313t', '.cpython-314t')):
+    if tag.startswith(('.cpython-313t', '.cpython-314t')):
         return None
 
     abi = '.abi3t' if get_config_var('Py_GIL_DISABLED') else '.abi3'
     platform = get_config_var('SOABI_PLATFORM')
-    _, ext = os.path.splitext(suffix)
+    # splitext() returns no extension for the untagged suffix ".so".
+    ext = suffix[suffix.rindex('.') :]
     return f'{abi}-{platform}{ext}' if platform else f'{abi}{ext}'
 
 
