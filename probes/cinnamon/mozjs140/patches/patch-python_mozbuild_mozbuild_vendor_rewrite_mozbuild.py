$NetBSD$

Python 3.15 removed ast.Str; construct and match ast.Constant instead.

--- python/mozbuild/mozbuild/vendor/rewrite_mozbuild.py.orig
+++ python/mozbuild/mozbuild/vendor/rewrite_mozbuild.py
@@ -327,7 +327,7 @@
     """
     if isinstance(node.value, ast.List) and "elts" in node.value._fields:
         for f in node.value.elts:
-            if not isinstance(f, ast.Constant) and not isinstance(f, ast.Str):
+            if not isinstance(f, ast.Constant):
                 log(
                     "Found non-constant source file name in list: ",
                     ast_get_source_segment(code, f),
