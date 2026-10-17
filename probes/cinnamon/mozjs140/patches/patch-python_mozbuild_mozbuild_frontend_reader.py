$NetBSD$

Python 3.15 removed ast.Str; construct and match ast.Constant instead.

--- python/mozbuild/mozbuild/frontend/reader.py.orig
+++ python/mozbuild/mozbuild/frontend/reader.py
@@ -470,7 +470,7 @@
             return c(
                 ast.Subscript(
                     value=c(ast.Name(id=self._global_name, ctx=ast.Load())),
-                    slice=c(ast.Index(value=c(ast.Str(s=node.id)))),
+                    slice=c(ast.Index(value=c(ast.Constant(value=node.id)))),
                     ctx=node.ctx,
                 )
             )
@@ -1039,7 +1039,7 @@
                 else:
                     # Others
                     assert isinstance(target.slice, ast.Index)
-                    assert isinstance(target.slice.value, ast.Str)
+                    assert isinstance(target.slice.value, ast.Constant)
                     key = target.slice.value.s
             elif isinstance(target, ast.Attribute):
                 assert isinstance(target.attr, str)
@@ -1051,10 +1051,10 @@
             value = node.value
             if isinstance(value, ast.List):
                 for v in value.elts:
-                    assert isinstance(v, ast.Str)
+                    assert isinstance(v, ast.Constant)
                     yield v.s
             else:
-                assert isinstance(value, ast.Str)
+                assert isinstance(value, ast.Constant)
                 yield value.s
 
         assignments = []
