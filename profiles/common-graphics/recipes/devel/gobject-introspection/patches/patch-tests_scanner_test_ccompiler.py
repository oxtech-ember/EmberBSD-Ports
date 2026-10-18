$NetBSD$

Origin: EmberBSD (AI-assisted).
Intercept the current setuptools compiler execution method in argument tests.
Keep the original spawn route for distutils versions without Compiler.call.
Preserve all assertions, skips and expected failures. No installed code changes.

--- tests/scanner/test_ccompiler.py.orig
+++ tests/scanner/test_ccompiler.py
@@ -81,7 +81,8 @@
         except ImportError as e:
             raise unittest.SkipTest(e)
 
-        with patch.object(distutils.ccompiler.CCompiler, 'spawn') as spawn:
+        method = 'call' if hasattr(distutils.ccompiler.CCompiler, 'call') else 'spawn'
+        with patch.object(distutils.ccompiler.CCompiler, method) as spawn:
             with Environ(environ):
                 cc = CCompiler(compiler_name=compiler_name)
                 # Avoid check if target is newer from source.
@@ -103,7 +104,8 @@
         except ImportError as e:
             raise unittest.SkipTest(e)
 
-        with patch.object(distutils.ccompiler.CCompiler, 'spawn') as spawn:
+        method = 'call' if hasattr(distutils.ccompiler.CCompiler, 'call') else 'spawn'
+        with patch.object(distutils.ccompiler.CCompiler, method) as spawn:
             with Environ(environ):
                 cc = CCompiler(compiler_name=compiler_name)
                 # Avoid check if target is newer from source.
