$NetBSD$

Use the C locale for LLD test commands. Lit does not inherit LC_ALL.
Darwin may use the user locale when no locale variable is present.
Origin: EmberBSD (AI-assisted).

--- test/lit.cfg.py.orig
+++ test/lit.cfg.py
@@ -16,2 +16,5 @@
 # name: The name of this test suite.
 config.name = "lld"
+
+# Keep diagnostics and timestamps stable across host locale settings.
+config.environment["LC_ALL"] = "C"
