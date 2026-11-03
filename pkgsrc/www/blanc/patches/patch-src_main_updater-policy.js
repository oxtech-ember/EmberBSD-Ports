$NetBSD$

Disable automatic application updates on NetBSD. Pkgsrc owns package updates.
Origin: EmberBSD (AI-assisted), based on Blanc v1.25.0.

--- src/main/updater-policy.js
+++ src/main/updater-policy.js
@@ -34,7 +34,10 @@
   return url.toString();
 }
 
-function resolveUpdaterPolicy({ isPackaged, env = process.env } = {}) {
+function resolveUpdaterPolicy({ isPackaged, env = process.env, platform = process.platform } = {}) {
+  if (platform === 'netbsd') {
+    return disabled('system packages own application updates');
+  }
   if (!isPackaged) return disabled('development builds do not self-update');
   const channel = String(env.BLANC_UPDATE_CHANNEL || '').trim();
   if (!channel) return production();
