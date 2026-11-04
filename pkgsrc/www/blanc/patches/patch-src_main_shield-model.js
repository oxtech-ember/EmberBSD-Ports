$NetBSD$

Use the independent Ember Browser icon and retain upstream attribution.
Origin: EmberBSD contributors (AI-assisted).

--- src/main/shield-model.js
+++ src/main/shield-model.js
@@ -68,7 +68,7 @@
 }
 
 // Blocker names are fixed product names, never translated.
-const providerName = (id) => (id === 'ublock-origin' ? 'uBlock Origin' : 'Blanc Blocker');
+const providerName = (id) => (id === 'ublock-origin' ? 'uBlock Origin' : 'Ember Browser Blocker');
 
 // Each text-producing function takes `t`, the interface translator.
 function shieldChipState({ url, blockedCount, excepted, adblockEnabled, provider = 'blanc', readiness = 'ready', t }) {
