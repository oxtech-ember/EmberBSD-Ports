$NetBSD$

Use the independent Ember Browser icon and retain upstream attribution.
Origin: EmberBSD contributors (AI-assisted).

--- src/renderer/pages/onboarding.js
+++ src/renderer/pages/onboarding.js
@@ -65,7 +65,7 @@
     busy: false,
     adblock: true,
     suggestions: true,
-    ping: true,
+    ping: false,
     // F52 spec D5: offered only on a fresh profile's first run (never on a
     // tour replay), preset on at After 7 days. Continue from the island step
     // saves it; Skip, or never reaching that Continue, leaves it Off.
