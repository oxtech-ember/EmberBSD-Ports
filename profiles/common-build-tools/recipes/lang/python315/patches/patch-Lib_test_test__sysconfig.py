$NetBSD$

Check the existing NetBSD pkgsrc packaging contract: EXT_SUFFIX is .so and
must be accepted by the loader. Upstream assumes it is the preferred suffix.
Keep test_soabi unchanged to verify tagged lookup priority, and keep the
original assertion on other platforms. Installed C extensions also exercise
plain, tagged and stable-ABI filename lookup in the target acceptance script.

Origin: EmberBSD (AI-assisted), adaptation to retained pkgsrc naming policy.
Not submitted or accepted upstream.

--- Lib/test/test_sysconfig.py.orig
+++ Lib/test/test_sysconfig.py
@@ -564,7 +564,14 @@
     @unittest.skipIf(not _imp.extension_suffixes(), "stub loader has no suffixes")
     def test_EXT_SUFFIX_in_vars(self):
         vars = sysconfig.get_config_vars()
-        self.assertEqual(vars['EXT_SUFFIX'], _imp.extension_suffixes()[0])
+        if sys.platform.startswith('netbsd'):
+            # pkgsrc keeps untagged modules in versioned Python directories.
+            # The loader must accept that spelling; test_soabi separately
+            # checks that tagged module names retain their lookup priority.
+            self.assertEqual(vars['EXT_SUFFIX'], '.so')
+            self.assertIn(vars['EXT_SUFFIX'], _imp.extension_suffixes())
+        else:
+            self.assertEqual(vars['EXT_SUFFIX'], _imp.extension_suffixes()[0])
 
     @unittest.skipUnless(sys.platform == 'linux', 'Linux-specific test')
     def test_linux_ext_suffix(self):
