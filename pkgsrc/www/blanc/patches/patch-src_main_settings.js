$NetBSD$

Use the independent Ember Browser icon and retain upstream attribution.
Origin: EmberBSD contributors (AI-assisted).

--- src/main/settings.js
+++ src/main/settings.js
@@ -316,10 +316,8 @@
   // never a password or service-account token, and never Profile Synced.
   onePasswordEnabled: false,
   onePasswordAccount: '',
-  // Anonymous "app launched" ping — see main/telemetry.js. On by default
-  // (opt-out in Settings); no browsing data, only version/OS plus a random
-  // per-install id used solely to count distinct active users.
-  usagePing: true,
+  // Upstream Blanc usage telemetry requires an explicit per-device opt-in.
+  usagePing: false,
   // Device-local completion marker for the compact first-run privacy card.
   // Existing profiles are promoted to the current version when their
   // pre-existing settings file is first opened; only a truly missing
