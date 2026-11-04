$NetBSD$

Use the independent Ember Browser identity. Origin: EmberBSD (AI-assisted).

--- src/main/local-profiles.js
+++ src/main/local-profiles.js
@@ -20,7 +20,7 @@
   function supportedRegistry() {
     const parsed = read();
     if (!parsed.supported) {
-      throw new Error('This Blanc build cannot modify a newer local-profile registry');
+      throw new Error('This Ember Browser build cannot modify a newer local-profile registry');
     }
     return parsed.registry;
   }
@@ -39,7 +39,7 @@
   function create(name) {
     const registry = supportedRegistry();
     if (registry.profiles.length >= MAX_LOCAL_PROFILES) {
-      throw new Error(`Blanc supports up to ${MAX_LOCAL_PROFILES} local profiles`);
+      throw new Error(`Ember Browser supports up to ${MAX_LOCAL_PROFILES} local profiles`);
     }
     const ordinal = registry.profiles.length + 1;
     const opaque = String(makeId()).replace(/[^a-zA-Z0-9_-]/g, '');
