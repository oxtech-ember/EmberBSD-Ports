$NetBSD$

Allow the upstream Intel test to find its XML fixture after relocation and
fail cleanly when it is missing. Installed Mesa libraries are unaffected.
Origin: EmberBSD contributors (AI-assisted).

--- src/intel/decoder/tests/genxml_test.c
+++ src/intel/decoder/tests/genxml_test.c
@@ -25,6 +25,7 @@
 
 #include <stdio.h>
 #include <stdint.h>
+#include <stdlib.h>
 #include <stdbool.h>
 #include "intel_decoder.h"
 
@@ -209,7 +210,14 @@
 
 int main(int argc, char **argv)
 {
-   struct intel_spec *spec = intel_spec_load_filename(GENXML_DIR, GENXML_FILE);
+   const char *dir = getenv("MESA_GENXML_TEST_DIR");
+   struct intel_spec *spec = intel_spec_load_filename(dir ? dir : GENXML_DIR,
+                                                      GENXML_FILE);
+   if (!spec) {
+      fprintf(stderr, "Cannot load genxml fixture %s from %s\n", GENXML_FILE,
+              dir ? dir : GENXML_DIR);
+      return 1;
+   }
 
    if (argc > 1 && strcmp(argv[1], "-quiet") == 0)
       quiet = true;
