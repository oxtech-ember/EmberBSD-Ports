$NetBSD$

Use the independent Ember Browser identity. Origin: EmberBSD (AI-assisted).

--- src/renderer/pages/settings.js
+++ src/renderer/pages/settings.js
@@ -383,7 +383,7 @@
     // fill-status-copy.js); these describe the Verify action itself.
     const VERIFY_ERRORS = {
       'account-not-found': 'Account not found — check your 1Password email address and try again.',
-      'not-authorized': '1Password didn’t authorize Blanc. Unlock 1Password, approve Blanc Browser, and try again.',
+      'not-authorized': '1Password didn’t authorize Ember Browser. Unlock 1Password, approve Ember Browser, and try again.',
       'session-expired': 'Authorization expired — try again.',
       'desktop-unavailable': '1Password isn’t available. Open the app and turn on Settings → Developer → Integrate with 1Password SDKs.',
       'timed-out': '1Password timed out — try again when the app is ready.',
@@ -442,7 +442,7 @@
     window.bowserPages.settings.onePasswordStatus().then(({ appDetected }) => {
       appHint.textContent = appDetected
         ? 'Installed on this Mac.'
-        : 'Blanc couldn’t find the 1Password app in Applications — if it’s installed elsewhere, Verify below still works.';
+        : 'Ember Browser couldn’t find the 1Password app in Applications — if it’s installed elsewhere, Verify below still works.';
       openAppButton.hidden = !appDetected;
     }).catch(() => { appHint.textContent = ''; });
     openAppButton.addEventListener('click', () => {
@@ -543,7 +543,7 @@
   }
 
   const appIconPlatform = navigator.platform;
-  const supportsNativeAppIcon = appIconPlatform.startsWith('Mac');
+  const supportsNativeAppIcon = false; // This build uses one independent icon.
   if (!supports('appIcon') || !supportsNativeAppIcon) {
     appIconSetting.remove();
   } else {
@@ -655,7 +655,7 @@
           const meta = document.createElement('div');
           meta.className = 'meta';
           meta.textContent = profile.id === 'default'
-            ? 'Your original Blanc data · permanent'
+            ? 'Your original Ember Browser data · permanent'
             : (profile.id === currentId ? 'Current window' : 'Separate local browser data');
           main.append(title, meta);
 
@@ -1100,7 +1100,7 @@
     });
 
     clearButton.addEventListener('click', async () => {
-      if (!confirm('Clear Blanc’s local crash history?')) return;
+      if (!confirm('Clear Ember Browser’s local crash history?')) return;
       const result = await window.bowserPages.diagnostics.clear();
       status.textContent = result.ok ? 'Crash history cleared.' : 'Couldn’t clear crash history.';
       renderDiagnostics(result);
