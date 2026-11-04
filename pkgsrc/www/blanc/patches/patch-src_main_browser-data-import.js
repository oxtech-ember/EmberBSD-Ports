$NetBSD$

Use the independent Ember Browser identity. Origin: EmberBSD (AI-assisted).

--- src/main/browser-data-import.js
+++ src/main/browser-data-import.js
@@ -19,7 +19,7 @@
 const CHROMIUM_EPOCH_OFFSET_MS = 11_644_473_600_000;
 
 const BROWSER_PERMISSION_GUIDANCE =
-  'macOS blocked access to this browser\'s profile folder. Grant Blanc Full Disk Access in System Settings → Privacy & Security, then try again.';
+  'macOS blocked access to this browser\'s profile folder. Grant Ember Browser Full Disk Access in System Settings → Privacy & Security, then try again.';
 
 function isBrowserAccessError(err) {
   return err?.code === 'EPERM' || err?.code === 'EACCES';
@@ -334,7 +334,7 @@
     if (!needsNormalQuit.has(newest.error)) return newest;
 
     // Older snapshots are preflight evidence only. They are never returned as
-    // the import source. A normal-quit prompt is allowed only when Blanc can
+    // the import source. A normal-quit prompt is allowed only when Ember Browser can
     // already prove that this profile has a saved, restorable session.
     for (const sessionName of sessionNames.slice(1)) {
       const recovery = await readSession(sessionName);
