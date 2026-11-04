$NetBSD$

Use the independent Ember Browser identity. Origin: EmberBSD (AI-assisted).

--- src/main/diagnostics-model.js
+++ src/main/diagnostics-model.js
@@ -159,7 +159,7 @@
     schemaVersion: 1,
     generatedAt: isoTime(generatedAt) ?? new Date(0).toISOString(),
     application: {
-      name: 'Blanc',
+      name: 'Ember Browser',
       version: safeVersion(appInfo.version),
       packaged: !!appInfo.packaged,
       electron: safeVersion(appInfo.electron),
