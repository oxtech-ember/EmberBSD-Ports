$NetBSD$

Check the NetBSD/Linux/Darwin pkgsrc packaging contract: EXT_SUFFIX is .so and
must be accepted by the loader. Upstream assumes it is the preferred suffix.
Keep test_soabi unchanged to verify tagged lookup priority, and keep the
original assertion on other platforms. Linux and Darwin ABI checks use the
preferred tagged loader suffix. Linux still checks machine and pointer width.
Installed C extensions also exercise
plain, tagged and stable-ABI filename lookup in the target acceptance script.

Origin: EmberBSD (AI-assisted), adaptation to retained pkgsrc naming policy.
Not submitted or accepted upstream.

--- Lib/test/test_sysconfig.py.orig
+++ Lib/test/test_sysconfig.py
@@ -571,13 +571,21 @@
     @unittest.skipIf(not _imp.extension_suffixes(), "stub loader has no suffixes")
     def test_EXT_SUFFIX_in_vars(self):
         vars = sysconfig.get_config_vars()
-        self.assertEqual(vars['EXT_SUFFIX'], _imp.extension_suffixes()[0])
+        if sys.platform in ('linux', 'darwin') or sys.platform.startswith('netbsd'):
+            # pkgsrc keeps untagged modules in versioned Python directories.
+            # The loader must accept that spelling; test_soabi separately
+            # checks that tagged module names retain their lookup priority.
+            self.assertEqual(vars['EXT_SUFFIX'], '.so')
+            self.assertIn(vars['EXT_SUFFIX'], _imp.extension_suffixes())
+        else:
+            self.assertEqual(vars['EXT_SUFFIX'], _imp.extension_suffixes()[0])
 
     @unittest.skipUnless(sys.platform == 'linux', 'Linux-specific test')
     def test_linux_ext_suffix(self):
         ctypes = import_module('ctypes')
         machine = platform.machine()
-        suffix = sysconfig.get_config_var('EXT_SUFFIX')
+        # Check the loader ABI; the pkgsrc build suffix is checked above.
+        suffix = _imp.extension_suffixes()[0]
         if re.match('(aarch64|arm|mips|ppc|powerpc|s390|sparc)', machine):
             self.assertTrue('linux' in suffix, suffix)
         if re.match('(i[3-6]86|x86_64)$', machine):
@@ -609,7 +617,8 @@
 
     @unittest.skipUnless(sys.platform == 'darwin', 'OS X-specific test')
     def test_osx_ext_suffix(self):
-        suffix = sysconfig.get_config_var('EXT_SUFFIX')
+        # Check the loader ABI; the pkgsrc build suffix is checked above.
+        suffix = _imp.extension_suffixes()[0]
         self.assertEndsWith(suffix, '-darwin.so')
 
     def test_always_set_py_debug(self):
