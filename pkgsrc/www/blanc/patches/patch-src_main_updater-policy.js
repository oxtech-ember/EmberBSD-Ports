$NetBSD$

Use the independent Ember Browser icon and retain upstream attribution.
Origin: EmberBSD contributors (AI-assisted).

--- src/main/updater-policy.js
+++ src/main/updater-policy.js
@@ -46,6 +46,7 @@
 function resolveUpdaterPolicy({
   isPackaged, env = process.env, platform = process.platform, isFlatpak = insideFlatpak,
 } = {}) {
+  if (platform === 'netbsd') return disabled('system packages own application updates');
   if (!isPackaged) return disabled('development builds do not self-update');
   const channel = String(env.BLANC_UPDATE_CHANNEL || '').trim();
   if (!channel) return production();
