$NetBSD$

Use the independent Ember Browser identity. Origin: EmberBSD (AI-assisted).

--- src/renderer/pages/error.js
+++ src/renderer/pages/error.js
@@ -10,7 +10,7 @@
   if (chromeWebStoreFailure) {
     document.getElementById('errorTitle').textContent = 'Chrome Web Store is temporarily unavailable';
     document.getElementById('errorDetail').textContent =
-      'This version of Blanc can’t safely open Chrome Web Store pages. Blanc blocked the page to prevent a browser crash.';
+      'This version of Ember Browser can’t safely open Chrome Web Store pages. Ember Browser blocked the page to prevent a browser crash.';
     document.getElementById('retryLink').hidden = true;
   } else if (certificateFailure) {
     document.getElementById('errorTitle').textContent = 'Your connection isn’t private';
