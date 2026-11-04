$NetBSD$

Use the independent Ember Browser identity. Origin: EmberBSD (AI-assisted).

--- src/renderer/pages/newtab.js
+++ src/renderer/pages/newtab.js
@@ -89,7 +89,7 @@
     const tabs = Number.isInteger(recovery.tabCount) ? recovery.tabCount : 0;
     const windows = Number.isInteger(recovery.windowCount) ? recovery.windowCount : 0;
     startupTitle.textContent = 'Pick up where you left off?';
-    startupMessage.textContent = `Blanc did not close normally. Restore ${tabs} ${tabs === 1 ? 'tab' : 'tabs'} across ${windows} ${windows === 1 ? 'window' : 'windows'}, or start with a clean Personal window. No saved website will open until you choose.`;
+    startupMessage.textContent = `Ember Browser did not close normally. Restore ${tabs} ${tabs === 1 ? 'tab' : 'tabs'} across ${windows} ${windows === 1 ? 'window' : 'windows'}, or start with a clean Personal window. No saved website will open until you choose.`;
     recoveryActions.hidden = false;
     if (recovery.error) {
       recoveryError.textContent = recovery.error;
@@ -104,8 +104,8 @@
         ? 'Retrying blocking…'
         : 'Preparing blocking…';
     startupMessage.textContent = failed
-      ? `Blanc has not opened queued web pages because its ad and tracker filters are unavailable. Retry, or explicitly continue with blocking turned off. Diagnostic: ${startup.error || 'unknown blocker initialization error'}`
-      : 'Blanc is preparing its local ad and tracker filters before opening web pages.';
+      ? `Ember Browser has not opened queued web pages because its ad and tracker filters are unavailable. Retry, or explicitly continue with blocking turned off. Diagnostic: ${startup.error || 'unknown blocker initialization error'}`
+      : 'Ember Browser is preparing its local ad and tracker filters before opening web pages.';
     startupActions.hidden = !failed;
     if (failed && startupWasHidden) startupRetry.focus();
   }
