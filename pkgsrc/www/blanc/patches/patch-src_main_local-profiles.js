$NetBSD$

Use the independent Ember Browser icon and retain upstream attribution.
Origin: EmberBSD contributors (AI-assisted).

--- src/main/local-profiles.js
+++ src/main/local-profiles.js
@@ -20,7 +20,7 @@
   function supportedRegistry() {
     const parsed = read();
     if (!parsed.supported) {
-      throw Object.assign(new Error('This Blanc build cannot modify a newer local-profile registry'), { code: 'registry-newer' });
+      throw Object.assign(new Error('This Ember Browser build cannot modify a newer local-profile registry'), { code: 'registry-newer' });
     }
     return parsed.registry;
   }
@@ -41,7 +41,7 @@
   function create(name, { defaultName = (ordinal) => `Profile ${ordinal}` } = {}) {
     const registry = supportedRegistry();
     if (registry.profiles.length >= MAX_LOCAL_PROFILES) {
-      throw Object.assign(new Error(`Blanc supports up to ${MAX_LOCAL_PROFILES} local profiles`), { code: 'profile-limit', limit: MAX_LOCAL_PROFILES });
+      throw Object.assign(new Error(`Ember Browser supports up to ${MAX_LOCAL_PROFILES} local profiles`), { code: 'profile-limit', limit: MAX_LOCAL_PROFILES });
     }
     const ordinal = registry.profiles.length + 1;
     const opaque = String(makeId()).replace(/[^a-zA-Z0-9_-]/g, '');
