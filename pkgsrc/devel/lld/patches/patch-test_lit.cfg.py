$NetBSD$

Use the C locale for LLD test commands. Lit does not inherit LC_ALL.
Darwin may use the user locale when no locale variable is present.
Origin: EmberBSD (AI-assisted).

--- test/lit.cfg.py.orig
+++ test/lit.cfg.py
@@ -15,6 +15,9 @@
 
 # name: The name of this test suite.
 config.name = "lld"
+
+# Keep diagnostics and timestamps stable across host locale settings.
+config.environment["LC_ALL"] = "C"
 
 # TODO: Consolidate the logic for turning on the internal shell by default for all LLVM test suites.
 # See https://github.com/llvm/llvm-project/issues/106636 for more details.
