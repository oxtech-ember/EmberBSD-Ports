$NetBSD$

Verify the NetBSD update policy and unaffected desktop platforms.
Origin: EmberBSD (AI-assisted), based on Blanc v1.25.0.

--- test/unit/updater-policy.test.js
+++ test/unit/updater-policy.test.js
@@ -2,7 +2,8 @@
 const test = require('node:test');
 const { resolveUpdaterPolicy } = require('../../src/main/updater-policy');
 
-const resolve = (env = {}, isPackaged = true) => resolveUpdaterPolicy({ isPackaged, env });
+const resolve = (env = {}, isPackaged = true, platform = process.platform) =>
+  resolveUpdaterPolicy({ isPackaged, env, platform });
 
 test('production stays on the embedded feed and development never updates', () => {
   assert.deepEqual(resolve(), {
@@ -10,6 +11,16 @@
     allowPrerelease: false, autoInstall: false, statusFile: null,
   });
   assert.equal(resolve({ BLANC_UPDATE_CHANNEL: 'staging', BLANC_UPDATE_STAGING_URL: 'https://updates.example/' }, false).enabled, false);
+});
+
+test('NetBSD packages use the system package manager for updates', () => {
+  assert.deepEqual(resolve({}, true, 'netbsd'), {
+    enabled: false, mode: 'disabled', reason: 'system packages own application updates', feed: null,
+    allowPrerelease: false, autoInstall: false, statusFile: null,
+  });
+  for (const platform of ['darwin', 'linux', 'win32']) {
+    assert.equal(resolve({}, true, platform).enabled, true);
+  }
 });
 
 test('staging requires exact valid configuration and never falls back', () => {
