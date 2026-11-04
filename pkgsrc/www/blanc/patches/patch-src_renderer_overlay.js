$NetBSD$

Use the independent Ember Browser icon and retain upstream attribution.
Origin: EmberBSD contributors (AI-assisted).

--- src/renderer/overlay.js
+++ src/renderer/overlay.js
@@ -3303,7 +3303,7 @@
   shieldPopRouteToggle.addEventListener('click', () => {
     window.browserAPI.routeActiveSite('toggle');
   });
-  function providerName(provider) { return provider === 'ublock-origin' ? 'uBlock Origin' : 'Blanc Blocker'; }
+  function providerName(provider) { return provider === 'ublock-origin' ? 'uBlock Origin' : 'Ember Browser Blocker'; }
 
   function resetShieldChoice() {
     shieldSaveGeneration += 1;
