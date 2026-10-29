$NetBSD$

Preserve a selected native stage runtime for scanner children on Darwin.

--- giscanner/scannermain.py.orig
+++ giscanner/scannermain.py
@@ -600,7 +600,23 @@
     return [common]
 
 
+def _emberbsd_native_runtime_view():
+    # Only the explicitly selected native stage supplies this build input.
+    if sys.platform != 'darwin':
+        return
+    view = os.environ.get('EMBERBSD_NATIVE_RUNTIME_VIEW', '')
+    if not view:
+        return
+    if not os.path.isabs(view) or os.pathsep in view or not os.path.isdir(view):
+        raise ValueError('invalid EMBERBSD_NATIVE_RUNTIME_VIEW: expected an absolute directory without colon')
+    paths = [p for p in os.environ.get('DYLD_LIBRARY_PATH', '').split(os.pathsep) if p]
+    if view not in paths:
+        paths.append(view)
+    os.environ['DYLD_LIBRARY_PATH'] = os.pathsep.join(paths)
+
+
 def scanner_main(args):
+    _emberbsd_native_runtime_view()
     parser = _get_option_parser()
     (options, args) = parser.parse_args(args)
 
