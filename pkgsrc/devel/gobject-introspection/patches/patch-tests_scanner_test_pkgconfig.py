$NetBSD$

Accept a POSIX pkg-config command with arguments from Meson.

--- tests/scanner/test_pkgconfig.py.orig
+++ tests/scanner/test_pkgconfig.py
@@ -45,6 +45,38 @@
 
 
 class PkgConfigTest(unittest.TestCase):
+
+    @unittest.skipIf(os.name == "nt", "POSIX command quoting")
+    def test_environment_command_arguments(self):
+        from unittest.mock import patch
+        import shlex
+        with pkg_config_script("""import sys; assert sys.argv[1:] == ['--define-prefix', '--libs', 'glib-2.0']""") as command:
+            value = ' '.join(shlex.quote(word) for word in command + ['--define-prefix'])
+            with patch.dict(os.environ, {'PKG_CONFIG': value}):
+                pkgconfig.libs(['glib-2.0'])
+        with patch.dict(os.environ, {'PKG_CONFIG': "tool --flag 'literal;$HOME'"}):
+            with patch('giscanner.pkgconfig.subprocess.check_output', return_value='') as run:
+                pkgconfig.check_output(['--libs'], False)
+                self.assertEqual(run.call_args.args[0], ['tool', '--flag', 'literal;$HOME', '--libs'])
+        for invalid in ('', '"unterminated'):
+            with patch.dict(os.environ, {'PKG_CONFIG': invalid}):
+                with self.assertRaisesRegex(pkgconfig.PkgConfigError, 'invalid PKG_CONFIG command'):
+                    pkgconfig.check_output([], False)
+
+    @unittest.skipIf(os.name == "nt", "POSIX executable script")
+    def test_environment_existing_path_with_spaces(self):
+        from unittest.mock import patch
+        import shlex
+        with tempfile.TemporaryDirectory() as directory:
+            path = os.path.join(directory, 'pkg config')
+            with open(path, 'w', encoding='utf-8') as script:
+                script.write('#!%s\nprint("-lworks")\n' % sys.executable)
+            os.chmod(path, 0o755)
+            with patch.dict(os.environ, {'PKG_CONFIG': path}):
+                self.assertEqual(pkgconfig.libs(['test']), ['-lworks'])
+            with patch.dict(os.environ, {'PKG_CONFIG': shlex.quote(path)}):
+                self.assertEqual(pkgconfig.libs(['test']), ['-lworks'])
+
 
     def test_non_zero_exit_code(self):
         """Checks that non-zero exit code from pkg-config results in exception."""
