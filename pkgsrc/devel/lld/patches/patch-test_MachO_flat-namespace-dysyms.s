$NetBSD$

Exercise loader-relative lookup from an indirect Mach-O dependency.

--- test/MachO/flat-namespace-dysyms.s.orig
+++ test/MachO/flat-namespace-dysyms.s
@@ -72,6 +72,17 @@
 # RUN:     -o %t/out 2>&1 | FileCheck --check-prefix=UNDEF %s
 # UNDEF: error: undefined symbol: _quux
 
+## The indirect load command in bar resolves relative to bar, even though
+## the explicitly linked baz lives in the parent directory.
+# RUN: mkdir -p %t/nested
+# RUN: %lld -dylib -install_name @loader_path/foo.dylib %t/foo.o -o %t/nested/foo.dylib
+# RUN: %lld -dylib -lSystem -install_name @loader_path/nested/bar.dylib %t/bar.o %t/nested/foo.dylib -o %t/nested/bar.dylib
+# RUN: %lld -dylib -lSystem %t/baz.o %t/nested/bar.dylib -o %t/outer.dylib
+# RUN: %lld -flat_namespace -lSystem %t/main.o %t/outer.dylib -o %t/nested-main -t | FileCheck --check-prefix=NESTED %s
+# NESTED: outer.dylib
+# NESTED: nested{{[/\\]}}bar.dylib
+# NESTED: nested{{[/\\]}}foo.dylib
+
 #--- foo.s
 .globl _foo
 _foo:
