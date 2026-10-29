$NetBSD$

Preserve boxed static functions while re-parsing GIR.

--- giscanner/girparser.py.orig
+++ giscanner/girparser.py
@@ -605,6 +605,9 @@
             func.is_inline = True
             func.is_method = True
             obj.methods.append(func)
+        for func in self._find_children(node, _corens('function')):
+            obj.static_methods.append(
+                self._parse_function_common(func, ast.Function, obj))
         for ctor in self._find_children(node, _corens('constructor')):
             obj.constructors.append(
                 self._parse_function_common(ctor, ast.Function, obj))
