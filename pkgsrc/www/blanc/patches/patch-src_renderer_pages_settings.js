$NetBSD$

Use the independent Ember Browser icon and retain upstream attribution.
Origin: EmberBSD contributors (AI-assisted).

--- src/renderer/pages/settings.js
+++ src/renderer/pages/settings.js
@@ -201,7 +201,7 @@
   const adblockEnabled = document.getElementById('adblockEnabled');
   if (supports('blockingStatus') && typeof window.bowserPages.settings.blockingStatus === 'function') {
     const selector = document.getElementById('adblockProvider');
-    const label = id => id === 'ublock-origin' ? 'uBlock Origin' : 'Blanc Blocker';
+    const label = id => id === 'ublock-origin' ? 'uBlock Origin' : 'Ember Browser Blocker';
     const renderBlocking = (state) => {
       if (!state) return;
       document.getElementById('blockingProviderSetting').hidden = state.exposed === false;
@@ -1249,7 +1249,7 @@
   }
 
   const appIconPlatform = navigator.platform;
-  const supportsNativeAppIcon = appIconPlatform.startsWith('Mac');
+  const supportsNativeAppIcon = false; // This build provides one independent icon.
   if (!supports('appIcon') || !supportsNativeAppIcon) {
     appIconSetting.remove();
   } else {
