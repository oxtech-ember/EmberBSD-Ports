# $NetBSD$

Use quickcheck 1.1 naming without deprecated API warnings.

--- bindgen-tests/tests/quickchecking/src/lib.rs.orig
+++ bindgen-tests/tests/quickchecking/src/lib.rs
@@ -103,6 +103,6 @@
 
     QuickCheck::new()
         .tests(tests)
-        .gen(Gen::new(generate_range))
+        .rng(Gen::new(generate_range))
         .quickcheck(bindgen_prop as fn(fuzzers::HeaderC) -> TestResult);
 }
